from docutils import nodes as doc_nodes
from docutils.parsers.rst import directives

from sphinx_design.dropdown import DropdownDirective


class DropdownTaglineDirective(DropdownDirective):
    """Extend sphinx-design dropdown with a :tagline: option.

    The tagline is inserted as an inline node in the dropdown summary title so
    it can be styled in CSS and hidden when the dropdown is open.
    """

    option_spec = dict(DropdownDirective.option_spec)
    option_spec["tagline"] = directives.unchanged

    def run_with_defaults(self):
        tagline = None
        for key in list(self.options):
            if key.replace("_", "-") == "tagline":
                tagline = self.options.pop(key)
                break

        out_nodes = super().run_with_defaults()

        if tagline:
            for root in out_nodes:
                if not isinstance(root, doc_nodes.Element):
                    continue

                # In sphinx-design dropdown AST, the first child is the title
                # rubric when a title is present.
                has_title = bool(root.get("has_title", False))
                if not has_title or len(root.children) == 0:
                    continue

                title_node = root.children[0]
                if not isinstance(title_node, doc_nodes.Element):
                    continue

                title_node += doc_nodes.inline(
                    "",
                    tagline,
                    classes=["sd-dropdown-tagline"],
                )
                break

        return out_nodes


def setup(app):
    # Override the directive name from sphinx-design so existing pages can use
    # :tagline: with .. dropdown:: directly.
    app.add_directive("dropdown", DropdownTaglineDirective, override=True)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
