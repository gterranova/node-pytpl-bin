#!/usr/bin/python
# -*- coding: utf-8 -*-

import htmlentitydefs
import re
import cStringIO as StringIO
import urllib

strfactory = lambda x: x
INDENT = '    '

class PythonCodeTag(object):
    """Constructs a new PythonCodeTag object, which can contain inner PythonCodeTag objects and text"""
    __slots__ = ["_attributes","_children"]
    def __init__(self,_attributes=None,_children=None):
        self._attributes = _attributes
        self._children = _children

    def _shallow_copy_update(_dict,_update):
        d = dict(_dict)
        d.update(_update)
        return d
    
    def __call__(self,*_children,**_attributes):
        """Calling on an instantiated PythonCodeTag object instantiates a new shallow copy of the tag or the tag updated
        In the copy the children are replaced by _children and the attributes are updated from _attributes"""
        if _attributes and self._attributes:
            _attributes = _shallow_copy_update(_attributes,self._attributes)

        # return a new PythonCodeTag
        if _children and _attributes:
            return PythonCodeTag(_attributes,_children)
        elif _attributes:
            return PythonCodeTag(_attributes,self._children)
        elif _children:
            return PythonCodeTag(self._attributes,_children)
        else:
            return self

    def __setitem__(self,_attribute,value):
        """Allow PythonCodeTag attributes to be updated like Python attributes"""
        # prevent assignment on hashable types other than strings
        if not isinstance(_attribute,basestring):
            raise TypeError("Invalid attribute name")
        if self._attributes is None: self._attributes = {}
        self._attributes[_attribute] = value

    def __getitem__(self,index):
        """Retrieve a child element from the PythonCodeTag"""
        if not isinstance(index,(int,long)):
            raise TypeError("Children must be indexed numerically")
        if not self._children:
            raise IndexError("list index out of range")
        return self._children[index]

    def render(self,fp=None,calldepth=0):
        """Pretty print the PythonCodeTag tree into a file object"""
        spaces = lambda: calldepth * INDENT
        
        if fp is None:
            fp = StringIO.StringIO()
            self.render(fp)
            fp.seek(0)
            return fp.read()

##        if self._children:
##            fp.write(u'\n' + spaces())

        newline = False
        if self._children:
            c = len(self._children)
            for i, child in enumerate(self._children):
                if hasattr(child,'render'):
                    newline = True
                    child.render(fp,calldepth + 1)                    
                else:
                    child = strfactory(child).strip()
                    if len(child.strip()) > 1:
                        newline = True
                        fp.write('\n' + spaces() + child)
                if newline and c > 1 and i == c-1:
                    fp.write(u'\n')
                
        if not newline and calldepth == 0:
            fp.write(u'\n')

class HTMLEscape(object):
    __lookuptable = None
    __escapefunc = None
    def __init__(self):
        if HTMLEscape.__lookuptable is None:
            HTMLEscape.__lookuptable = {}
            for codepoint,name in htmlentitydefs.codepoint2name.iteritems():
                if codepoint <= 127:
                    HTMLEscape.__lookuptable[chr(codepoint)] = '&amp;%s; ' % name
                else:
                    HTMLEscape.__lookuptable[unichr(codepoint)] = '&amp;#%d; ' % codepoint

        if HTMLEscape.__escapefunc is None:
            HTMLEscape.__escapefunc = re.compile('(%s)' % ('|'.join(list(HTMLEscape.__lookuptable))))

    def escape(self,_encodedhtml):
        _replace = lambda matchobj: HTMLEscape.__lookuptable.get(matchobj.group(0), '?')
        return HTMLEscape.__escapefunc.sub(_replace,_encodedhtml)

    def canescape(self,_char):
        return _char in HTMLEscape.__lookuptable

def render_html_block(block,fp=None,calldepth=0):
    """Constructs a new HTMLTag object, which can contain inner HTMLTag objects and text"""
    __unpairedtags = frozenset('br input img hr link meta iframe'.split())
    __noescaping = frozenset('script cdata raw'.split())
    __noformatting = frozenset('pre'.split())
    __htmlents = HTMLEscape()
    __wrapchildcount = 1
    
    """Pretty print the HTMLTag tree into a file object"""
    spaces = lambda: calldepth * INDENT
    noindent = lambda: (calldepth>1 and calldepth-1 or 0) * INDENT
    child_wrap_p = block.children and (len(block.children) >= __wrapchildcount) # and hasattr(block.children[-1],'render'))
    
    if fp is None:
        fp = StringIO.StringIO()
        render_html_block(block,fp)
        fp.seek(0)
        return fp.read()

    if block.tag == 'raw':
        if  len(block.args) > 0 and len(block.args[0]) > 0:
            fp.write(u'\n' + spaces() + block.args[0])
    
    elif block.tag != 'cdata':
        unpaired_terminator = ""
        if block.tag in __unpairedtags:
            unpaired_terminator = " /"
        if block.kwargs:
            fp.write(u'\n' + spaces() + u'<%s %s%s>' % (block.tag,' '.join([x for x in [u"%s='%s'" % (k,v) for k,v in block.kwargs.iteritems()]]),unpaired_terminator))
        else:
            fp.write(u'\n' + spaces() + u'<%s%s>' % (block.tag,unpaired_terminator))
    else:
        fp.write(u'\n' + spaces() + u'<![CDATA[')

    if block.children:
        for child in block.children:
            render_html_block(child,fp,calldepth+1)
                    
    if block.tag not in ('cdata', 'raw') and block.tag not in __unpairedtags:
        # sets a boolean flag to determin if we can wrap
        if block.tag not in __noformatting and child_wrap_p:
            fp.write(u'\n' + spaces() + '</%s>' % block.tag)
        else:
            fp.write(u'</%s>' % block.tag)
    elif block.tag == 'cdata':
        fp.write(u']]>')
    elif block.tag == 'raw':
        pass
##            fp.write('\n' + spaces())

    if calldepth == 0:
        fp.write(u'\n')

def render_python_block(block,fp=None,calldepth=0):
    
    """Pretty print the HTMLTag tree into a file object"""
    spaces = lambda: calldepth * INDENT

    if fp is None:
        fp = StringIO.StringIO()
        render_python_block(block,fp)
        fp.seek(0)
        return fp.read()

    newline = False

    if block.tag == 'raw':
        if  len(block.args) > 0 and len(block.args[0]) > 0:
            fp.write(u'\n' + spaces() + block.args[0])

    if block.children:
        c = len(block.children)
        for i, child in enumerate(block.children):
            render_python_block(child,fp,calldepth+1)
        if c > 1:
            fp.write(u'\n')
    
    if calldepth == 0:
        fp.write(u'\n')
