#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os
import errno
import codecs 
from cStringIO import StringIO
import simpleparser, pprint
from myeval import SimpleEval, SimpleExec, TempEval, GLOBALS
from stackdict import StackDict
from codetag import render_html_block, render_python_block

import datetime

TEMPLATES = {}
EDITABLE_BLOCKS = {}

import re

tidy = lambda c: re.sub(
    r'(^\s*[\r\n]+|^\s*\Z)|(\s*\Z|\s*[\r\n]+)',
    lambda m: (u'',u'\n')[m.lastindex == 2],
    c)

def debug_mode():
    return os.environ.get('DEBUG', 'OFF') == 'ON'

##str_factory = lambda x: unicode(x).encode('utf-8')
def str_factory(s):
    try:
        return s.encode('utf-8')
    except:
        return s

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

FOR_REGEX  = re.compile(r"""^(?P<names>\w+(?:\s*,\s*\w+)*)\s+in\s+(?P<iter>.+)$""")
            
def converts(*args):
    def _inner(func):
        func._converter_for = frozenset(args)
        return func
    return _inner
    
class ConverterBase(object):
    def __init__(self, converters=None):

        if not converters:
            converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, '_converter_for'):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self.converters = converters
        self.fout = None

    def process(self, items, env=StackDict(), refs=StackDict(), use_code=False):
        ret = []
        do_else = False
        inline_block = None

        for item0 in items:
            item = item0.copy(env)
##            if DEBUG:
##                print repr(item)
            
            if item.entry_type != simpleparser.BlockTypes.EDITABLE and item.tag[2:5] != "END" and inline_block != None:
                TEMPLATES['EDITABLE'][inline_block].append(item)
                continue
            
            if item.entry_type == simpleparser.BlockTypes.DEFAULT:
                item.tag = 'raw'
                if item.can_eval:
                    item.args = [TempEval(x.strip(), env) for x in item.args]
            if item.entry_type == simpleparser.BlockTypes.REF:
                if item.tag in refs:
                    ref = refs.pop()
                    ret.extend(self.process(ref[item.tag], env, refs, use_code))
                    del ref[item.tag]
                    refs.push(ref)

            elif item.entry_type == simpleparser.BlockTypes.EDITABLE:
                if item.tag[2:10] == "EDITABLE":
                    inline_block = item.args[0]
                    TEMPLATES.setdefault("EDITABLE", {})
                    item.entry_type = simpleparser.BlockTypes.DEFAULT
                    item.args = ["%s %r" % (item.tag, str(inline_block))]
                    TEMPLATES['EDITABLE'][inline_block] = [item]
                    continue
                elif item.tag[2:5] == "END":
                    item.entry_type = simpleparser.BlockTypes.DEFAULT
                    item.args = [item.tag]                    
                    TEMPLATES['EDITABLE'][inline_block].append(item)
                    if inline_block in EDITABLE_BLOCKS:
                        ret.extend(self.process(EDITABLE_BLOCKS[inline_block], env=env, use_code=use_code))
                    else:
                        ret.extend(self.process(TEMPLATES['EDITABLE'][inline_block], env=env, use_code=use_code))
                    inline_block = None
                    continue
                else:
                    print "UNKNOWN %s" % item.tag

            elif item.entry_type == simpleparser.BlockTypes.TEMPLATE:
                    TEMPLATES[item.tag] = item

            elif item.entry_type == simpleparser.BlockTypes.CODE:
                if item.tag == "python":
                    env.push()
                    env.update(item.kwargs)
                    env.update({'args': item.args})
                    old_stdout = sys.stdout
                    code = u''.join(filter(None, [render_python_block(x).decode('utf-8') for x in self.process(item.children, env=env, use_code=True) if x is not None]))
                    code = TempEval(code, env)
                    redirected_output = sys.stdout = StringIO()
                    try:
                        env.update(SimpleExec(code, env))
                    except:
                        raise
                    sys.stdout = old_stdout                    
                    value = redirected_output.getvalue()
                    if len(value.strip()) > 0:
##                        ret.append(simpleparser.Block(0, 'raw', args=[redirected_output.getvalue()], kwargs=item.kwargs, children=[], filename=item.filename, linecount=item.linecount))
                        ret.append(simpleparser.Block(0, 'raw', args=[redirected_output.getvalue()], kwargs=item.kwargs, children=[]))
                    env.pop()
                elif item.tag.startswith('debug '):
                    os.environ['DEBUG'] = eval(item.tag.split()[1]) and 'ON' or 'OFF'
                    print "Debug mode %s" % os.environ['DEBUG']
                else:
                    try:
                        cmd, exp = item.tag.split(' ',1)
                    except:
                        cmd = item.tag
                        exp = ''

                    if cmd == 'if':
                        cond = bool(SimpleEval(exp, env))
                        do_else = not cond
                        if cond:
                            ret.extend(self.process(item.children, env, refs, use_code))
                    elif cmd == 'elif':
                        if do_else:                        
                            cond = bool(SimpleEval(exp, env))
                            do_else = not cond
                            if cond:
                                ret.extend(self.process(item.children, env, refs, use_code))
                    elif cmd == 'else':
                        if do_else:
                            do_else = False
                            ret.extend(self.process(item.children, env, refs, use_code))
                            
                    elif cmd == 'for':
                        cond = FOR_REGEX.match(exp)
                        if cond is None:
                            raise Exception("Invalid 'for ...' at '%s'." % exp)
                        
                        names = tuple(n.strip()  for n in cond.group("names").split(","))
                        iterable = cond.group("iter")

                        do_else = True

                        try:
                            loop_iter = iter(SimpleEval(iterable, env))
                        except TypeError:
                            raise Exception("Cannot loop over '%s'." % iterable)
                        env.push()
                        for i in loop_iter:
                            do_else = False
                            if len(names) == 1:
                                env[names[0]] = i
                            else:
                                env.update(dict(zip(names, i)))   #"for a,b,.. in list"
                            ret.extend(self.process(item.children, env, refs, use_code))
                        env.pop()
                    else:
                        env.update(SimpleExec(item.tag, env))
                    
            else:
##                env.update(item.kwargs)

                if item.entry_type == simpleparser.BlockTypes.TAG and item.tag in TEMPLATES:
                    tmpl = TEMPLATES[item.tag].copy(env)

                    ## copy default params
                    params = {}
                    for i, k in enumerate(tmpl.args + tmpl.kwargs.keys()):
                        try:
                            params[k] = item.args[i]
                        except:
                            if k in item.kwargs:
                                params[k] = item.kwargs[k]
                            elif k in tmpl.kwargs:
                                params[k] = tmpl.kwargs[k]
##                            else:
##                                params[k] = None
                    env.push(params)
                    env.update({'args': item.args})
                    env.update({'kwargs': item.kwargs})
                    refs.push({'children': item.children})
                    ret.extend(self.process(tmpl.children, env=env, refs=refs, use_code=use_code))
                    env.pop()
                    refs.pop()
                else:                    
                    if item.tag in self.converters:
                        converter = self.converters[item.tag]
                        sub = converter(item, env)
                        if type(sub) == list:
                            ret.extend(sub)
                        elif sub != None:
                            ret.append(sub)                            
                    else:
                        if item.tag != 'raw' and use_code:
    ##                        raise Exception("Macro %r not defined (in %s line %d)" % (item.tag, item.filename, item.linecount))
                            raise Exception("Macro %r not defined: %r" % (item.tag,item))

                        item_processed = item.copy(env)
                        item_processed.children = self.process(item.children, env=env, refs=refs, use_code=use_code)
                        
                        ret.append(item_processed)

        return ret

        
    def process_file(self, fname, fout=None, env=StackDict()):
        global GLOBALS
        global EDITABLE_BLOCKS, TEMPLATES

        GLOBALS = {}
        self.fout = fout
        if fout != None:
            use_code = fout.endswith('.py.flt') or fout.endswith('.py')
        else:
            use_code = fname.endswith('.py.flt') or fname.endswith('.py')

        old_dir = os.getcwd()
        os.chdir(os.path.dirname(fname))       
        
        if fout != None and os.path.exists(fout):
            ret = self.process(simpleparser.load(fout), env=env, use_code=use_code)
            if 'EDITABLE' in TEMPLATES:
                EDITABLE_BLOCKS = TEMPLATES['EDITABLE'].copy()
            TEMPLATES = {}
            GLOBALS = {}

        blocks = self.process(simpleparser.load(fname), env=env, use_code=use_code)
        output = self.process_blocks(blocks, fout, env=env)
        os.chdir(old_dir)
        return output
        
    def process_blocks(self, blocks, fout=None, env=StackDict()):
        if fout != None:
            if fout.endswith('.flt'):
                fout = fout[:-4]
            save_processed_file = os.path.splitext(fout)[1] != ''
            renderer = fout.endswith('.py') and render_python_block or render_html_block
        else:
            save_processed_file = False
            renderer = render_html_block            
        
        output = u''.join(filter(None, [renderer(x).decode('utf-8') for x in blocks if x is not None]))
        output = output.replace("<NEWLINE>", "")
        output = output.strip()+'\n'

        if not save_processed_file:
            return output

        mkdir_p(os.path.dirname(fout))
        f = save_processed_file and codecs.open(fout, 'w', "utf-8") or codecs.getwriter('utf8')(sys.stdout)        
        f.write(output)
        if fout:
            f.close()
        return output

class ConverterWithExtras(ConverterBase):
    @converts('import')
    def conv_import(self, item, env=StackDict()):
        fname = os.path.realpath(TempEval(item.args[0]))

        if not os.path.exists(fname):
            raise Exception("%s not found in %s" % (fname, os.getcwd()))

        old_dir = os.getcwd()
        os.chdir(os.path.dirname(fname))
        
        p = simpleparser.Parser()
        blocks = p.process_file(fname)
        use_code = fname.endswith('.py')
        ret = self.process(blocks, env=env, use_code=use_code)
        os.chdir(old_dir)
        return ret
    
    @converts('export')
    def conv_export(self, item, env=StackDict()):
        global GLOBALS
        global EDITABLE_BLOCKS, TEMPLATES
        
        fout = TempEval(item.args[0])

        fout = os.path.join(os.path.dirname(self.fout), fout)
        if debug_mode():
            print "-> Export to %s" % fout
        mkdir_p(os.path.dirname(fout))
##        if os.path.exists(fout):
##            ret = self.process(simpleparser.Parser().process_file(fout), env.copy())
##            if 'EDITABLE' in TEMPLATES:
##                EDITABLE_BLOCKS = TEMPLATES['EDITABLE'].copy()
##            TEMPLATES = {}
##            GLOBALS = {}
        try:
            blocks = self.process(item.children, env=env, use_code=fout.endswith('.py'))
        except:
            print "Error processing %s (USECODE %r): %r" % (fout, fout.endswith('.py'), item.children)
            raise
        self.process_blocks(blocks, fout, env)


def convert(fname, fout=None, env=StackDict()):
    print "Converting %s to %s" % (fname, fout)
    converter = ConverterWithExtras()
    if type(env) == dict:
        env = StackDict(env)
    return converter.process_file(fname, fout, env)

if __name__ == "__main__":
    params = [os.path.realpath(p) for p in sys.argv[1:]]
    convert(*params)

