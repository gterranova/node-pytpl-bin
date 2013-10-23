#!/usr/bin/python
# -*- coding: utf-8 -*-

class StackDict(object):
    def __init__(self, env={}):
        self.stack = [env]

    @property
    def globals(self):
        return self.stack[0]

    @property
    def locals(self):
        return self.stack[-1]

    def __getitem__(self, key):
        for stack in reversed(self.stack):
            if key in stack:
                return stack[key]
        raise Exception("'" + key + "'" + " is not in the stack")

    def __setitem__(self, key, value):
        for stack in reversed(self.stack):
            if key in stack:
                stack[key] = value
                return
        self.stack[-1][key] = value

    def __contains__(self, key):
        for stack in reversed(self.stack):
            if key in stack:
                return True
        return False
        
    def pop(self):
        return self.stack.pop()

    def push(self, stack={}):
        self.stack.append(stack)

    def update(self, d):
        for k in d:
            self[k] = d[k]
##        self.stack[-1].update(d)

    def to_dict(self):
        ret = {}
        for stack in self.stack:
            ret.update(stack)
        return ret

    def is_empty(self):
        return len(self.stack) == 1 and self.stack[0] == {}

