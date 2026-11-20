"""Read the attributes of the benchmark classes from their source.

This allows getting class attributes, such as ``requirements``, without
importing the modules, which may fail before installing the dependencies.
"""
import ast
import inspect
from pathlib import Path


def _resolve_class_def(module_file, name, benchmark_dir, before=None,
                       seen=()):
    """Find the class ``name`` defined or imported in ``module_file``.

    Only ``class name`` and ``from module import name [as alias]``, at the
    top level before line ``before``, are followed, for modules of the
    benchmark. Return ``(file, ClassDef)``, or None.
    """
    if (module_file, name) in seen:
        return None
    seen = (*seen, (module_file, name))
    try:
        tree = ast.parse(module_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None

    # Imports protected by a `safe_import_context` are in a with block.
    binding = None
    for node in tree.body:
        for stmt in node.body if isinstance(node, ast.With) else [node]:
            if before is not None and stmt.lineno >= before:
                break
            if isinstance(stmt, ast.ClassDef) and stmt.name == name:
                binding = stmt
            elif isinstance(stmt, ast.ImportFrom):
                binding = next((
                    (stmt, a.name) for a in stmt.names
                    if (a.asname or a.name) == name
                ), binding)

    if binding is None or isinstance(binding, ast.ClassDef):
        return binding and (module_file, binding)
    stmt, name = binding
    parts = stmt.module.split('.') if stmt.module else []
    if 0 < stmt.level <= len(module_file.parents):
        base = module_file.parents[stmt.level - 1]
    elif stmt.level == 0 and parts[:1] == ['benchmark_utils']:
        base = benchmark_dir
    else:
        return None
    path = base.joinpath(*parts)
    src = next((
        c.resolve() for c in [path.with_suffix('.py'), path / '__init__.py']
        if c.is_file()
    ), None)
    return src and _resolve_class_def(src, name, benchmark_dir, seen=seen)


def _c3_merge(sequences):
    """Merge the linearizations of the bases, as Python builds the MRO."""
    sequences = [list(s) for s in sequences if s]
    merged = []
    while sequences:
        # The first head that is in no other tail goes next.
        head = next(
            (s[0] for s in sequences
             if not any(s[0] in other[1:] for other in sequences)),
            None
        )
        if head is None:
            raise TypeError("Inconsistent MRO.")
        merged.append(head)
        sequences = [s[1:] if s[0] == head else s for s in sequences]
        sequences = [s for s in sequences if s]
    return merged


def _get_mro(module_file, class_def, benchmark_dir, classes, stack=()):
    """MRO of the classes defined in the benchmark, as keys of ``classes``.

    ``classes`` maps each key ``(file, lineno)`` to ``(file, ClassDef)``.
    """
    key = (module_file, class_def.lineno)
    classes[key] = (module_file, class_def)
    base_mros = []
    for base in class_def.bases:
        found = isinstance(base, ast.Name) and _resolve_class_def(
            module_file, base.id, benchmark_dir, before=class_def.lineno
        )
        if found and (found[0], found[1].lineno) not in stack:
            base_mros.append(_get_mro(
                *found, benchmark_dir, classes, stack=(*stack, key)
            ))
    try:
        return [key, *_c3_merge([*base_mros, [m[0] for m in base_mros]])]
    except TypeError:
        # Python cannot build this class either: keep its own attributes.
        return [key]


def _get_class_nodes(module_file, class_name, benchmark_dir):
    """Map the attributes of a class to ``(node, file)``, following its MRO.

    ``node`` is the value expression for an assignment, or the function
    definition for a method, and ``file`` is the module defining it. Return
    None if the class is not found.
    """
    found = _resolve_class_def(module_file, class_name, benchmark_dir)
    if found is None:
        return None
    classes = {}
    mro = _get_mro(*found, benchmark_dir, classes)

    nodes = {}
    # From the last class of the MRO, so the first ones take precedence.
    for key in mro[::-1]:
        class_file, class_def = classes[key]
        for node in class_def.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes[node.name] = (node, class_file)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign)
                    else [node.target]
                )
                for target in targets:
                    if isinstance(target, ast.Name) and node.value:
                        nodes[target.id] = (node.value, class_file)
    return nodes


def get_class_attrs(module_file, base_cls, benchmark_dir):
    """Get the attributes of a benchmark class without importing it.

    The class is the one named after ``base_cls`` in ``module_file``, e.g.
    ``Solver`` for ``BaseSolver``. Its attributes are read from its source
    and from the bases defined in the benchmark, in the same module or in
    ``benchmark_utils``, following the MRO. Bases from other packages, such
    as benchopt's base classes, are skipped.

    Parameters
    ----------
    module_file : Path
        File of the module defining the class.
    base_cls : type
        Base class of the component, e.g. ``BaseSolver``. Its public
        attributes, such as ``requirements`` or ``parameters``, and its
        methods are the ones collected, along with ``name``.
    benchmark_dir : Path
        Folder of the benchmark, to locate the ``benchmark_utils`` modules.

    Returns
    -------
    attrs : dict or None
        The attributes set by the class or its bases. A data attribute maps
        to its value, or to an ``AttributeError`` when it is not a literal,
        and a method to its ``ast.FunctionDef``. None if the class is not
        found.
    """
    module_file = Path(module_file).resolve()
    benchmark_dir = Path(benchmark_dir).resolve()
    cls_name = base_cls._base_class_name
    nodes = _get_class_nodes(module_file, cls_name, benchmark_dir)
    if nodes is None:
        return None

    # Attributes ending with `_` are computed, e.g. `dataset_`.
    names = ['name'] + [
        p.name for p in inspect.classify_class_attrs(base_cls)
        if not p.name.startswith('_') and not p.name.endswith('_')
    ]
    attrs = {}
    for attr, (node, attr_file) in nodes.items():
        if attr not in names:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            attrs[attr] = node
            continue
        try:
            attrs[attr] = ast.literal_eval(node)
        except Exception:
            attrs[attr] = AttributeError(
                f"Could not evaluate statically '{attr}' of the class "
                f"{cls_name} in {attr_file}.\nBy default, this should be a "
                "string literal. If dynamic evaluation is necessary, use "
                "`safe_import_context`."
            )
    return attrs
