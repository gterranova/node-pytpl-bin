#!/usr/bin/env node
'use strict';
var spawn = require('child_process').spawn;
var binPath = require('../lib/pytpl').path;

spawn('python.exe', [binPath, process.argv[2], process.argv[3]], { stdio: 'inherit' })
	.on('exit', process.exit);
