import click
from docutils import nodes
from docutils import statemachine
from sphinx.util import logging
from sphinx.util import nodes as sphinx_nodes

from sphinx_click.ext import ClickDirective as _ClickDirective
from sphinx_click.ext import _format_command
from sphinx_click.ext import _format_description
from sphinx_click.ext import _filter_commands
from sphinx_click.ext import NESTED_FULL


LOG = logging.getLogger(__name__)
CLICK_VERSION = tuple(int(x) for x in click.__version__.split('.')[0:2])


class ClickDirective(_ClickDirective):

    def _generate_nodes(self, name, command, parent, nested, commands=None,
                        semantic_group=False):
        """Generate the relevant Sphinx nodes.

        Format a `click.Group` or `click.Command`.

        :param name: Name of command, as used on the command line
        :param command: Instance of `click.Group` or `click.Command`
        :param parent: Instance of `click.Context`, or None
        :param nested: The granularity of subcommand details.
        :param commands: Display only listed commands or skip the section if
            empty
        :param semantic_group: Display command as title and description for
            CommandCollection.
        :returns: A list of nested docutil nodes
        """
        ctx = click.Context(command, info_name=name, parent=parent)

        if CLICK_VERSION >= (7, 0) and command.hidden:
            return []

        # Title
        section = nodes.section(
            '',
            nodes.title(text=name),
            ids=[nodes.make_id(ctx.command_path)],
            names=[nodes.fully_normalize_name(ctx.command_path)],
        )

        # Summary
        source_name = ctx.command_path
        result = statemachine.ViewList()

        if semantic_group:
            lines = _format_description(ctx)
        else:
            lines = _format_command(ctx, nested, commands)

        for line in lines:
            LOG.debug(line)
            result.append(line, source_name)

        sphinx_nodes.nested_parse_with_titles(self.state, result, section)

        # Subcommands

        if nested == NESTED_FULL:
            if isinstance(command, click.CommandCollection):
                for source in command.sources:
                    section.extend(
                        self._generate_nodes(source.name, source, ctx, nested,
                                             semantic_group=True)
                    )
            else:
                commands = _filter_commands(ctx, commands)
                for command in commands:
                    parent = ctx if not semantic_group else ctx.parent
                    section.extend(
                        self._generate_nodes(command.name, command, parent,
                                             nested)
                    )

        return [section]


def setup(app):
    app.add_directive('click', ClickDirective)
