"""Trusted resume layout generated from Markdown structure, never raw HTML."""
from xml.etree import ElementTree as ET

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class _ResumeLayout(Treeprocessor):
    def run(self, root):
        children = list(root)
        output = []
        index = 0
        while index < len(children):
            node = children[index]
            if node.tag == 'p' and not len(node) and node.text == '[pagebreak]':
                output.append(ET.Element('div', {'class': 'page-break', 'aria-hidden': 'true'}))
            elif (node.tag in {'h3', 'h4'} and index + 1 < len(children)
                  and self._is_metadata(children[index + 1])):
                group = ET.Element('div', {'class': 'entry-head'})
                group.extend((node, children[index + 1]))
                output.append(group)
                index += 1
            else:
                output.append(node)
            index += 1
        root[:] = output

    @staticmethod
    def _is_metadata(node):
        return (node.tag == 'p' and not (node.text or '').strip()
                and len(node) == 1 and node[0].tag == 'em'
                and not (node[0].tail or '').strip())


class ResumeLayoutExtension(Extension):
    def extendMarkdown(self, md):
        # Inline emphasis is resolved at priority 20; prettification runs at 10.
        md.treeprocessors.register(_ResumeLayout(md), 'resume_layout', 15)
