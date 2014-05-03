#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os
from simpleconverter import convert

import fancyopts

# Command options and aliases are listed here, alphabetically
globalopts = [
    ('c', 'config', 'config.json', 'config file'),
    ('i', 'input', 'instance.json', 'input file'),
    ('a', 'appdir', '', 'app dir (where app files are located) (default: the dir of the input file)'),
    ('', 'defaults', False, 'generate defaults'),
    ('v', 'verbose', False, 'show verbose output (include headers)'),
    ('', 'debug', None, 'enable debugging output'),
    ('', 'version', None, 'output version information and exit'),
    ('h', 'help', None, 'display help and exit')
]

def usage(s=''):
    print "\n%s - python template processor" % os.path.basename(sys.argv[0])
    if len(s):
        print "\n%s" %s
    print "\nUsage: %s <input file> <output file> <OPTIONS>" % os.path.basename(sys.argv[0])
    option_lists = []
    option_lists.append(("Options:", globalopts))

    # list all option lists
    opt_output = []
    for title, options in option_lists:
        opt_output.append(("\n%s" % title, None))
        for option in options:
            if len(option) == 5:
                shortopt, longopt, default, desc, optlabel = option
            else:
                shortopt, longopt, default, desc = option
                optlabel = "VALUE" # default label

            
            if isinstance(default, list):
                numqualifier = " %s [+]" % optlabel
            elif (default is not None) and not isinstance(default, bool):
                numqualifier = " %s" % optlabel
            else:
                numqualifier = ""
            opt_output.append(("%2s%s" %
                               (shortopt and "-%s" % shortopt,
                                longopt and " --%s%s" %
                                (longopt, numqualifier)),
                               "%s%s" % (desc,
                                         default
                                         and " (default: %s)" % default
                                         or "")))
    for opt, desc in opt_output:
        if desc:
            print "%s %s" % (opt, desc)
        else:
            print "%s" % opt


def parsecmdline(args=sys.argv):
    options = {}

    try:
        args = fancyopts.fancyopts(args, globalopts, options, True)
    except fancyopts.getopt.GetoptError, inst:
        raise Exception("error.CommandError(None, %r)" % inst)

    return options

if __name__ == "__main__":
    if len(sys.argv) > 2:
        filePair = map(os.path.abspath, sys.argv[1:3])
    else:
        usage("Invalid number of arguments")
        exit(1)

    if not os.path.exists(filePair[0]):
        usage("File %s does not exists." % os.path.basename(filePair[0]))
        exit(1)
            
    options = {}
    env = {}
    
    if len(sys.argv) > 3:
        options = parsecmdline(sys.argv[3:])
        if options['help']:
            usage()
            exit(1)
        env['configFile'] = os.path.abspath(options['config']).replace('\\','/')
        env['inputFile'] = os.path.abspath(options['input']).replace('\\','/')
        
        if options.get('appdir', '') == '':
            appdir = os.path.dirname(env['inputFile'])
        else:
            appdir = options['appdir']
            
        env['appDir'] = os.path.abspath(appdir).replace('\\','/')
        env['generateDefaults'] = options['defaults']

    if options['verbose']:        
        for k in options:
            print " %s=%r" % (k, options[k])

    convert(*filePair, env=env)

