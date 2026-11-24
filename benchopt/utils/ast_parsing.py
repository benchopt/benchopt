"""Read the attributes of the benchmark classes from their source.

This allows getting class attributes, such as ``requirements``, without
importing the modules, which may fail before installing the dependencies.
"""
import ast
import inspect
from pathlib import Path

from .parametrized_name_mixin import merge_declared_attrs


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

    # Find the last ClassDef or import of `name` before line `before`.
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

    # For an import, look up the class in the imported module.
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
    """Merge the linearizations of the bases, as Python builds the MRO.

    A class comes after all the classes that derive from it. For
    ``class A(B, C)`` with ``B(D)`` and ``C(D)``, the MRO is A, B, C, D,
    while a depth-first walk would give A, B, D, C.
    """
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

    ``classes`` maps each key ``(file, lineno)`` to ``(file, ClassDef, mro)``.
    """
    key = (module_file, class_def.lineno)
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
        mro = [key, *_c3_merge([*base_mros, [m[0] for m in base_mros]])]
    except TypeError:
        # Python cannot build this class either: keep its own attributes.
        mro = [key]
    classes[key] = (module_file, class_def, mro)
    return mro


def _get_class_nodes(class_def):
    """Map the attributes set in the body of ``class_def`` to their node.

    ``node`` is the value expression for an assignment, or the function
    definition for a method.
    """
    nodes = {}
    for node in class_def.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                node.targets if isinstance(node, ast.Assign)
                else [node.target]
            )
            for target in targets:
                if isinstance(target, ast.Name) and node.value:
                    nodes[target.id] = node.value
    return nodes


def _literal_eval(node, class_file, class_def, benchmark_dir, merged):
    """Evaluate ``node``, with ``**Base.parameters`` for a base in ``merged``.

    ``merged`` maps the classes of the MRO to their merged attributes.
    """
    if not isinstance(node, ast.Dict):
        return ast.literal_eval(node)
    value = {}
    for k, v in zip(node.keys, node.values):
        if k is not None:
            value[ast.literal_eval(k)] = ast.literal_eval(v)
            continue
        found = (
            isinstance(v, ast.Attribute) and v.attr == 'parameters'
            and isinstance(v.value, ast.Name) and _resolve_class_def(
                class_file, v.value.id, benchmark_dir, before=class_def.lineno
            )
        )
        if not found or (found[0], found[1].lineno) not in merged:
            raise ValueError(f"Cannot evaluate {ast.unparse(v)}.")
        value.update(merged[found[0], found[1].lineno].get('parameters', {}))
    return value


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
        The attributes set by the class or its bases, with ``requirements``
        and ``parameters`` merged along the MRO. A data attribute maps
        to its value, or to an ``AttributeError`` when it is not a literal,
        and a method to its ``ast.FunctionDef``. None if the class is not
        found.
    """
    module_file = Path(module_file).resolve()
    benchmark_dir = Path(benchmark_dir).resolve()
    cls_name = base_cls._base_class_name
    found = _resolve_class_def(module_file, cls_name, benchmark_dir)
    if found is None:
        return None
    classes = {}
    mro = _get_mro(*found, benchmark_dir, classes)

    # Attributes ending with `_` are computed, e.g. `dataset_`.
    names = ['name'] + [
        p.name for p in inspect.classify_class_attrs(base_cls)
        if not p.name.startswith('_') and not p.name.endswith('_')
    ]
    declared, merged = {}, {}
    for key in mro[::-1]:
        class_file, class_def, class_mro = classes[key]
        attrs = {}
        for attr, node in _get_class_nodes(class_def).items():
            if attr not in names:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                attrs[attr] = node
                continue
            try:
                attrs[attr] = _literal_eval(
                    node, class_file, class_def, benchmark_dir, merged
                )
            except Exception:
                attrs[attr] = AttributeError(
                    f"Could not evaluate statically '{attr}' of the class "
                    f"{cls_name} in {class_file}.\nBy default, this should "
                    "be a string literal. If dynamic evaluation is necessary, "
                    "use `safe_import_context`."
                )
        declared[key] = attrs
        merged[key] = merge_declared_attrs(
            declared[k] for k in class_mro[::-1]
        )
    attrs = {k: v for d in declared.values() for k, v in d.items()}
    attrs.update(merged[mro[0]])
    return attrs
