#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, re
import cStringIO as StringIO
import pprint

from myeval import SimpleEval, SimpleExec, TempEval
from stackdict import StackDict
from ordereddict import OrderedDict

regex = re.compile(r"([^=]*)='(([^'\\]*(?:\\.[^'\\]*)*))'(?:\s+|$)",re.IGNORECASE|re.UNICODE|re.DOTALL | re.VERBOSE)
QUOTES = ['\'','"']
EQUAL = u'='
SPACES = [' ','\t','\r', '\n']

BLOCK_TYPES = [('#@', 'TAG'), ('#%','TEMPLATE'), ('#!','CODE'), ('#&','REF')]
BLOCK_DICT = dict(BLOCK_TYPES)
class BlockTypesBase(object):
    @classmethod
    def get(cls, s):
        
        if s[:2] in BLOCK_DICT:
            entry_type = getattr(cls,BLOCK_DICT[s[:2]])
            if entry_type == cls.CODE and s[2] == '/':
                return cls.DEFAULT
            return entry_type
        return cls.DEFAULT
    
BlockTypes = type('BlockTypes', (BlockTypesBase,), dict([(x[1], i+2) for i, x in enumerate(BLOCK_TYPES)]+[('DEFAULT',0),('EDITABLE', 1)]))

DATATYPES_MAP = [(str, r'[^\d]+'),(int, r'^-?\d+$'), (float, r'^\d+\.\d+$')]

def debug_mode():
    return os.environ.get('DEBUG', 'OFF') == 'ON'

class Block(object):
    def __init__(self, entry_type, tag, args=[], kwargs=OrderedDict(), children=[], filename='', linecount=0, can_eval=True):
        self.entry_type = entry_type
        self.tag = tag
        self.args = args
        self.kwargs = kwargs
        self.children = []
        self.can_eval = can_eval
##        self.filename = filename
##        self.linecount = linecount

    def append(self, sub):
        self.children = sub

    def copy(self, env=StackDict()):
        _type = self.entry_type
        _tag = self.tag
        _args = self.args
        _kwargs = self.kwargs
        
##        if not env.is_empty():
        if self.can_eval:
            _tag = TempEval(_tag, env)
            try:
                _args = [TempEval(x, env) for x in _args]
                _kwargs = OrderedDict([(k, SimpleEval(TempEval(_kwargs[k], env), env)) for k in _kwargs])
            except:
##                print "In %s line %d: %r" % (self.filename, self.linecount, self)
                raise
##            print dict([(k, env[k]) for k in _args+_kwargs.keys() if k in env])
            
        b = Block(_type, _tag, _args, _kwargs, can_eval=self.can_eval)
        b.children = self.children[:]
##        b.filename= self.filename
##        b.linecount = self.linecount
        return b        

    def __repr__(self):
##        return "<block type=%r tag=%r args=%r kwargs=%r children=%r, filename=%r linecount=%r>" % (self.entry_type > 1 and BLOCK_TYPES[self.entry_type-2][1] or ('DEFAULT','EDITABLE')[self.entry_type], self.tag, self.args, self.kwargs, self.children, self.filename, self.linecount)
        return "<block type=%r tag=%r args=%r kwargs=%r children=%r>" % (self.entry_type > 1 and BLOCK_TYPES[self.entry_type-2][1] or ('DEFAULT','EDITABLE')[self.entry_type], self.tag, self.args, self.kwargs, self.children)
        
def guess_type(s):
    s = s.decode('string_escape')
    for key, reg in DATATYPES_MAP:
        if re.match(reg,s):
            return key(s)
    return s

class Parser(object):
    def __init__(self):
        self.reset()
##        self.filename = filename
        self.fn = None
##        self.linecount = 0

    def reset(self):
        self.kwargs_list = []
        self.args_list = []
        self.token = ''
        self.key = ''
        self.value = ''
        self.quote_start = None
        self.is_quoted = False
        self.slash = None
        
    def append(self):
        
        if self.key == '':
            self.key = self.token
            self.value = None
        else:
            self.value = self.token

        if self.key != '':
            if self.value is None:
                if not self.is_quoted:
                    self.key = guess_type(self.key)
                self.args_list.append( self.key )
            else:
                if not self.is_quoted:
                    self.value = guess_type(self.value)
                self.kwargs_list.append( (self.key, self.value) )
                
        self.key = self.value = self.token = ''

    def addc(self, c):
        if self.slash:
            self.token += self.slash
            self.slash = None
        self.token += c
        
    def process_entry(self, s):

        self.reset()

        if len(s) > 2 and s[0] in QUOTES and s[0] == s[-1]:
            if s[0] == s[1] == s[2] == s[-3] == s[-2] == s[-1]:
                return Block(BlockTypes.DEFAULT, 'raw', args=[s.encode('utf-8').decode('string_escape')], can_eval=False)
            can_eval = s[1:].startswith("#@import") or s[1:].startswith("#@export") or s[1:].startswith("#!")
            return Block(BlockTypes.DEFAULT, 'raw', args=[s[1:-1].encode('utf-8').decode('string_escape')], can_eval=can_eval)

        if len(s) > 3 and s[0] == '#' and s[1] in QUOTES and s[1] == s[-1]:
            return Block(BlockTypes.DEFAULT, 'raw', args=[s[2:-1].encode('utf-8').decode('string_escape')], can_eval=False)

        entry_type = BlockTypes.get(s)

        if len(s) > 2 and (s[2:10] == "EDITABLE" or s[2:5] == "END"):
            entry_type = BlockTypes.EDITABLE

        elif entry_type == BlockTypes.DEFAULT:
            return Block(BlockTypes.DEFAULT, 'raw', args=[s.encode('utf-8').decode('string_escape')])

        elif entry_type == BlockTypes.CODE:
            if len(s) > 2 and s[2:].startswith("debug "):
                os.environ['DEBUG'] = eval(s.split()[-1]) and 'ON' or 'OFF'
                return Block(entry_type, s[2:])
            
            elif len(s) > 2 and not s[2:].startswith("python "):
                return Block(entry_type, s[2:])

        elif entry_type == BlockTypes.REF:
            return Block(entry_type, s[2:])
        
        try:
            if entry_type != BlockTypes.EDITABLE:
                identif, kwargs_str = s[2:].split(' ',1)
            else:
                identif, kwargs_str = s.split(' ',1)
                
        except ValueError:
            if entry_type != BlockTypes.EDITABLE:
                identif = s[2:]
                kwargs_str = ''
            else:
                identif = s
                kwargs_str = ''

        for c in kwargs_str:

            if c in QUOTES:
                # if is escaped
                if self.slash != None and c == self.quote_start:
                    self.token += c
                    self.slash = None
                    
                elif self.quote_start != None:
                    # close string
                    if c == self.quote_start:
                        self.quote_start = None
                    # quote inside a string
                    else:
                        self.addc(c)
                # open string
                else:
                    self.quote_start = c
                    self.is_quoted=True

            elif c == u'\\':
                self.slash = c

            elif self.quote_start != None:
                self.addc(c)
                    
            elif c in SPACES:
                # space inside string
                if self.quote_start != None:
                    self.addc(c)
                else:
                    self.append()
                    self.is_quoted = False

            elif c == EQUAL:
                self.key = self.token
                self.token = u''
                
            else:
                self.addc(c)

        self.append()
        self.is_quoted = False            
        args_list = self.args_list[:]
        kwargs_list = self.kwargs_list[:]
        self.args_list = []
        self.kwargs_list = []
        if self.quote_start != None and debug_mode():
            print "UNTERMINED QUOTED STRING", entry_type, identif, args_list, OrderedDict(kwargs_list)
        
        r = Block(entry_type, identif, args_list, OrderedDict(kwargs_list))
        return r    


    def process_line(self, line):
        counting_spaces = True
        spaces = 0
        entry = u''

        for c in line.rstrip():
            if c == u' ' and counting_spaces:
                spaces += 1
            else:
                counting_spaces = False
                entry = line.rstrip()[spaces:]
                break
        return (spaces, entry)

    
    def process_file(self, fname=None, src=None):
        if fname:
            self.fn = open(fname, 'rb')
        else:
            self.fn  = StringIO.StringIO(src)
        
        levels = [[]]
        block = []
        indents = [0]
        sub = None
        full_entry = u''
        original_spaces = None
        
        while True:
            line = self.fn.readline()
##            self.linecount = self.linecount + 1
            line = line.decode('utf-8')
            if not line:
                break   

            counting_spaces = True
            spaces = 0
            entry = u''

            for c in line.rstrip():
                if c == u' ' and counting_spaces:
                    spaces += 1
                else:
                    counting_spaces = False
                    entry = line.rstrip()[spaces:]
                    break

            full_entry += entry

            if entry == u'':
    ##            full_entry = u''
                continue

            if entry[-1] == "\\":
                full_entry = full_entry[:-1]
                if original_spaces is None:
                    original_spaces = spaces
                continue

            if original_spaces is not None:
                spaces = original_spaces
                original_spaces = None
                
            if spaces == indents[-1]:
                pass
                
            elif spaces > indents[-1]:
                levels.append([])
                indents.append(spaces)

            else:
                while (spaces < indents[-1]):
                    indents.pop()
                    sub = levels.pop()
                    current_level = levels[-1][-1]
                    current_level.append(sub)

            block = self.process_entry(full_entry)
##            block.filename=self.filename
##            block.linecount=self.linecount

            levels[-1].append( block )

            full_entry = u''

        self.fn.close()
        self.fn = None
        
        while len(indents) > 1:
            indents.pop()
            sub = levels.pop()
            current_level = levels[-1][-1]
            current_level.append(sub)

        return levels[0]

   
def load(fname):
    p = Parser()
    return p.process_file(fname)
    
if __name__ == "__main__":
    pprint.pprint( load('test.txt') )    
    p = Parser()
    pprint.pprint( p.process_file(None, """
div class_name="row"
    ${';'.join(['aaaa','bbb'])}
    )
    
    ssss
        ]
"""))


