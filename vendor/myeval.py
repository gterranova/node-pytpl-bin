#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, re

GLOBALS = {}

def SimpleEval(v, env):
    GLOBALS.update(env.to_dict())

    if type(v) not in (str, unicode):
        return v

    if len(v) == 0:
        return v

    try:
        return eval(v, GLOBALS)
    except:
##        g = GLOBALS.copy()
##        g['__builtins__'] = "HIDDEN"
##        print "\n", "*"*40, "\nUnable to eval %s %r, globals %r\n" % (type(v), v, g), "*"*40, "\n"
        return v

def SimpleExec(v, env):
    GLOBALS.update(env.to_dict())

    if type(v) not in (str, unicode):
        return v

    if len(v) == 0:
        return v

    try:
##        exec(TempEval(v, env), GLOBALS)
        exec(v, GLOBALS)
    except NameError:
        g = GLOBALS.copy()
        g['__builtins__'] = "HIDDEN"
        msg = "\n"+"*"*40+"\nUnable to exec: %r, globals %r\n" % (v, g)+"*"*40+"\n"
        print msg
        raise
    except TypeError:
        g = GLOBALS.copy()
        g['__builtins__'] = "HIDDEN"
        msg = "\n"+"*"*40+"\nUnable to exec: %r, globals %r\n" % (v, g)+"*"*40+"\n"
        sys.stderr.write( msg)
        raise

    return GLOBALS

def TempEval(template, env=None):
    if type(template) not in (str, unicode):
        return template

    if len(template) == 0:
        return template
    
    mark = re.compile('\${([^\$]*?)}')
    t = template
    if env == None:
        stack = {}
    else:
        stack = env.to_dict()
    for item in mark.findall(template):
        try:
##            GLOBALS.update(env.to_dict())
            v = eval(item, stack)
            t = t.replace(u'${%s}'%item, str(v))
        except:
##            g = GLOBALS.copy()
##            g['__builtins__'] = "HIDDEN"
##            print "\n", "*"*40, "\nUnable to exec: %r, globals %r\n" % (item, g), "*"*40, "\n", t
##            raise
            pass

    return t

