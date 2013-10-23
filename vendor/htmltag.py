import htmlentitydefs
import re
import cStringIO as StringIO
import urllib

strfactory = lambda x: x
INDENT = '    '

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

class raw_text(object):
    def __init__(self, text):
        self.text = text
        
    def render(self,fp=None,calldepth=0):
        fp.write(self.text.encode('utf-8')) 
        
class Tag(object):
    """HTMLTag Factory"""
    def __getattr__(self,_type):
        return HTMLTag(_type)

class HTMLTag(object):
    """Constructs a new HTMLTag object, which can contain inner HTMLTag objects and text"""
    __unpairedtags = frozenset('br input img hr link meta iframe'.split())
    __noescaping = frozenset('script cdata raw'.split())
    __noformatting = frozenset('pre'.split())
    __indent = frozenset('-'.split())
    __raw = frozenset('raw'.split())
    __htmlents = HTMLEscape()
    __wrapchildcount = 1

    __slots__ = ["_type","_attributes","_children"]
    def __init__(self,_type,_attributes=None,_children=None):
        self._type = _type.lower()
        self._attributes = _attributes
        self._children = _children

    def _shallow_copy_update(_dict,_update):
        d = dict(_dict)
        d.update(_update)
        return d
    
    def __call__(self,*_children,**_attributes):
        """Calling on an instantiated HTMLTag object instantiates a new shallow copy of the tag or the tag updated
        In the copy the children are replaced by _children and the attributes are updated from _attributes"""
        if _attributes and self._attributes:
            _attributes = _shallow_copy_update(_attributes,self._attributes)
        # replace 'klass' with 'class', must be 'klass' in Python to prevent name conflict
        klass = _attributes.pop("klass",None)
        if klass: _attributes['class'] = klass
        # return a new HTMLTag
        if _children and _attributes:
            return HTMLTag(self._type,_attributes,_children)
        elif _attributes:
            return HTMLTag(self._type,_attributes,self._children)
        elif _children:
            return HTMLTag(self._type,self._attributes,_children)
        else:
            return self

    def __setitem__(self,_attribute,value):
        """Allow HTMLTag attributes to be updated like Python attributes"""
        # prevent assignment on hashable types other than strings
        if not isinstance(_attribute,basestring):
            raise TypeError("Invalid attribute name")
        if self._attributes is None: self._attributes = {}
        self._attributes[_attribute] = value

    def __getitem__(self,index):
        """Retrieve a child element from the HTMLTag"""
        if not isinstance(index,(int,long)):
            raise TypeError("Children must be indexed numerically")
        if not self._children:
            raise IndexError("list index out of range")
        return self._children[index]

    def render(self,fp=None,calldepth=0):
        """Pretty print the HTMLTag tree into a file object"""
        spaces = lambda: calldepth * INDENT
        noindent = lambda: (calldepth>1 and calldepth-1 or 0) * INDENT
        child_wrap_p = self._children and (len(self._children) >= HTMLTag.__wrapchildcount and hasattr(self._children[-1],'render'))
        
        if fp is None:
            fp = StringIO.StringIO()
            self.render(fp)
            fp.seek(0)
            return fp.read()

##        if calldepth == 0:
##            fp.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">')
##            fp.write('<!DOCTYPE html>')
        if self._type == '-':
            fp.write(u'\n' + spaces())
            
        elif self._type == 'raw':
            fp.write(u'\n' + spaces())
        
        elif self._type != 'cdata':
            unpaired_terminator = ""
            if self._type in HTMLTag.__unpairedtags:
                unpaired_terminator = " /"
            if self._attributes:
##                fp.write('\n' + spaces() + '<%s %s%s>' % (self._type,' '.join([x for x in ["%s='%s'" % (k,v) for k,v in self._attributes.iteritems()]]).encode('utf-8'),unpaired_terminator))
                fp.write(u'\n' + spaces() + u'<%s %s%s>' % (self._type,' '.join([x for x in [u"%s='%s'" % (k,v) for k,v in self._attributes.iteritems()]]),unpaired_terminator))
            else:
                fp.write(u'\n' + spaces() + u'<%s%s>' % (self._type,unpaired_terminator))
        else:
            fp.write(u'\n' + spaces() + u'<![CDATA[')

        if self._children:
            for child in self._children:
                if hasattr(child,'render'):
                    if self._type == 'raw':
                        child.render(fp,calldepth + 1)
                    else:
                        child.render(fp,calldepth + 1)
                elif self._type in HTMLTag.__noescaping:
##                    fp.write(str(child).encode('utf-8'))
                    fp.write(strfactory(child))
                else:
##                    child = str(child)
                    child = strfactory(child)
                    try:
                        for char in child:
                            if HTMLTag.__htmlents.canescape(char):
                                raise ValueError
                    except ValueError:
                        # child contained a value that needed escaping
                        child = HTMLTag.__htmlents.escape(child)
                    if len(child.strip()) > 1:
##                        fp.write(child.encode('utf-8'))
                        fp.write(child)
                        
        if self._type not in ('cdata','-', 'raw') and self._type not in HTMLTag.__unpairedtags:
            # sets a boolean flag to determin if we can wrap
            if self._type not in HTMLTag.__noformatting and child_wrap_p:
                fp.write(u'\n' + spaces() + '</%s>' % self._type)
            else:
                fp.write(u'</%s>' % self._type)
        elif self._type == 'cdata':
            fp.write(u']]>')
        elif self._type == 'raw':
            pass
##            fp.write('\n' + spaces())

        if calldepth == 0:
            fp.write(u'\n')

