"""Read the attributes of the benchmark classes from their source.

This allows getting class attributes, such as ``requirements``, without
importing the modules, which may fail before installing the dependencies.
"""
import ast
import inspect
from pathlib import Path


def _parse_module(module_file):
    """Parse a module file, or return None if it cannot be read."""
    try:
        return ast.parse(Path(module_file).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None


def _resolve_module_file(module, level, from_file, benchmark_dir):
    """Return the file of a module defined in the benchmark, or None."""
    parts = module.split('.') if module else []
    if 0 < level <= len(from_file.parents):
        base = from_file.parents[level - 1]
    elif level == 0 and parts and parts[0] == 'benchmark_utils':
        base = benchmark_dir
    else:
        return None
    path = base.joinpath(*parts)
    candidates = [path.with_suffix('.py')] if parts else []
    candidates.append(path / '__init__.py')
    return next((c.resolve() for c in candidates if c.is_file()), None)


def _resolve_class_def(module_file, parts, benchmark_dir, before=None,
                       seen=None):
    """Find the class bound to the dotted name ``parts`` in ``module_file``.

    Only the top-level statements before line ``before`` are considered, and
    imports are followed when they point to a module of the benchmark. Return
    ``(file, ClassDef)``, or None if the class is not defined statically in
    the benchmark.
    """
    seen = set() if seen is None else seen
    key = (module_file, before, *parts)
    tree = _parse_module(module_file)
    if key in seen or tree is None:
        return None
    seen.add(key)

    # Imports protected by a `safe_import_context` are in a with block.
    statements = [
        stmt for node in tree.body
        for stmt in ([node, *node.body] if isinstance(node, ast.With)
                     else [node])
    ]
    head, binding, star_imports = parts[0], None, []
    for node in statements:
        if before is not None and node.lineno >= before:
            break
        if isinstance(node, ast.ClassDef) and node.name == head:
            binding = node
        elif isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == head
                for t in node.targets):
            # `Base = Other` rebinds the name, to a class we may not resolve.
            binding = node
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname == head:
                    binding = (alias.name, 0, None)
                elif alias.asname is None and alias.name.split('.')[0] == head:
                    binding = (head, 0, None)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == '*':
                    star_imports.append((node.module, node.level))
                elif (alias.asname or alias.name) == head:
                    binding = (node.module, node.level, alias.name)

    if binding is None:
        # The name may come from a `from module import *`, the last first.
        for module, level in star_imports[::-1]:
            src = _resolve_module_file(module, level, module_file,
                                       benchmark_dir)
            found = src and _resolve_class_def(
                src, parts, benchmark_dir, seen=seen
            )
            if found:
                return found
        return None
    if isinstance(binding, ast.ClassDef):
        return (module_file, binding) if len(parts) == 1 else None
    if isinstance(binding, ast.Assign):
        if not isinstance(binding.value, (ast.Name, ast.Attribute)):
            return None
        value_parts = ast.unparse(binding.value).split('.')
        return _resolve_class_def(
            module_file, value_parts + parts[1:], benchmark_dir,
            before=binding.lineno, seen=seen
        )
    module, level, name = binding
    if name is not None:
        # `from module import name`: `name` is a class, or a submodule
        # when it is used as `name.Class`.
        if len(parts) == 1:
            src = _resolve_module_file(module, level, module_file,
                                       benchmark_dir)
            return src and _resolve_class_def(
                src, [name], benchmark_dir, seen=seen
            )
        module = '.'.join(p for p in [module, name] if p)
    # `import module`: the class is `module.sub.Class`.
    module = '.'.join([module, *parts[1:-1]])
    src = _resolve_module_file(module, level, module_file, benchmark_dir)
    return src and _resolve_class_def(
        src, parts[-1:], benchmark_dir, seen=seen
    )


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
        found = _resolve_class_def(
            module_file, ast.unparse(base).split('.'), benchmark_dir,
            before=class_def.lineno
        )
        if found is not None and (found[0], found[1].lineno) not in stack:
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
    found = _resolve_class_def(module_file, [class_name], benchmark_dir)
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
