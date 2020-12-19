"""Provide a convenient way to link to GitHub issues and pull requests.

Adapted from:
https://doughellmann.com/blog/2010/05/09/defining-custom-roles-in-sphinx/
"""
from docutils.nodes import reference
from docutils.parsers.rst.roles import set_classes


def gh_role(name, rawtext, pr_number, lineno, inliner, options={}, content=[]):
    """Link to a GitHub pull request."""
    ref = f'https://github.com/benchopt/benchOpt/pull/{pr_number}'
    set_classes(options)
    node = reference(rawtext, '#' + pr_number, refuri=ref, **options)
    return [node], []


def setup(app):
    """Do setup."""
    app.add_role('gh', gh_role)
    return
