import click
from docutils import nodes
from docutils.parsers.rst import directives
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

    option_spec = {
        **_ClickDirective.option_spec,
        'semantic-group': directives.unchanged,
    }

    def _generate_nodes(self, name, command, parent, nested, commands=None,
                        semantic_group=None):
        """Generate the relevant Sphinx nodes.

        Format a `click.Group` or `click.Command`.

        :param name: Name of command, as used on the command line
        :param command: Instance of `click.Group` or `click.Command`
        :param parent: Instance of `click.Context`, or None
        :param nested: The granularity of subcommand details.
        :param commands: Display only listed commands or skip the section if
            empty
        :param semantic_group: Display this as title with the command
            description.
        :returns: A list of nested docutil nodes
        """
        ctx = click.Context(command, info_name=name, parent=parent)

        if CLICK_VERSION >= (7, 0) and command.hidden:
            return []

        # Title
        label = name
        base_id = ctx.command_path
        if semantic_group is not None:
            label = semantic_group
            base_id = f'{base_id}-{semantic_group}'

        section = nodes.section(
            '',
            nodes.title(text=label),
            ids=[nodes.make_id(base_id)],
            names=[nodes.fully_normalize_name(base_id)],
        )

        # Summary
        source_name = ctx.command_path
        result = statemachine.ViewList()

        if semantic_group is None:
            lines = _format_command(ctx, nested, commands)
        else:
            lines = _format_description(ctx)

        for line in lines:
            LOG.debug(line)
            result.append(line, source_name)

        sphinx_nodes.nested_parse_with_titles(self.state, result, section)

        # Subcommands

        if nested == NESTED_FULL:
            commands = _filter_commands(ctx, commands)
            for command in commands:
                section.extend(
                    self._generate_nodes(command.name, command, ctx, nested)
                )

        return [section]

    def run(self):
        self.env = self.state.document.settings.env

        command = self._load_module(self.arguments[0])

        if 'prog' not in self.options:
            raise self.error(':prog: must be specified')

        prog_name = self.options.get('prog')
        nested = self.options.get('nested')

        show_nested = 'show-nested' in self.options
        if show_nested:
            raise self.error("':show-nested:' has been removed")

        commands = self.options.get('commands')
        semantic_group = self.options.get('semantic-group')

        return self._generate_nodes(
            prog_name, command, None, nested, commands, semantic_group
        )


def setup(app):
    app.add_directive('click', ClickDirective)
