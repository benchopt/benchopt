from docutils import nodes as doc_nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives

from sphinx_design.dropdown import DropdownDirective


class DropdownTaglineBlockDirective(Directive):
    """Multiline tagline block for dropdown headers.

    Usage inside a dropdown body:

    .. dropdown-tagline::

       First line with *rst*.
       Second line.
    """

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = True
    option_spec = {}

    def run(self):
        container = doc_nodes.container(classes=["sd-dropdown-tagline-block"])
        self.state.nested_parse(self.content, self.content_offset, container)
        return [container]


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

            # Support multiline tagline content from a dedicated nested
            # directive by transforming its block children into line items.
            tagline_blocks = [
                child
                for child in root.children[1:]
                if isinstance(child, doc_nodes.Element)
                and "sd-dropdown-tagline-block" in child.get("classes", [])
            ]
            if tagline_blocks:
                block = tagline_blocks[0]
                tagline_inline = doc_nodes.inline(
                    "",
                    "",
                    classes=["sd-dropdown-tagline"],
                )

                def _add_line_from_children(children):
                    tagline_inline.append(
                        doc_nodes.inline(
                            "",
                            "",
                            *[c.deepcopy() for c in children],
                            classes=["sd-dropdown-tagline-line"],
                        )
                    )

                for child in block.children:
                    if isinstance(child, doc_nodes.paragraph):
                        _add_line_from_children(child.children)
                    elif isinstance(child, doc_nodes.bullet_list):
                        for item in child.children:
                            if not isinstance(item, doc_nodes.list_item):
                                continue
                            if len(item.children) == 0:
                                continue
                            first = item.children[0]
                            if isinstance(first, doc_nodes.paragraph):
                                line_children = [doc_nodes.Text("- ")] + [
                                    c.deepcopy() for c in first.children
                                ]
                                _add_line_from_children(line_children)
                title_node += tagline_inline
                block.parent.remove(block)
                break

            if tagline:
                tagline_nodes, tagline_messages = self.state.inline_text(
                    tagline, self.lineno
                )
                title_node += doc_nodes.inline(
                    "",
                    "",
                    *tagline_nodes,
                    classes=["sd-dropdown-tagline"],
                )
                title_node += tagline_messages
                break

        return out_nodes


def setup(app):
    # Override the directive name from sphinx-design so existing pages can use
    # :tagline: with .. dropdown:: directly.
    app.add_directive("dropdown", DropdownTaglineDirective, override=True)
    app.add_directive("dropdown-tagline", DropdownTaglineBlockDirective)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
