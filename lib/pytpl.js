'use strict';
var path = require('path');
var url = require('url');

var target = {
	name: 'pytpl.py',
	pathPrefix: '../vendor'
};

function getPathToPythonScript(target) {

	var targetPath = [];
	var exec = target.name;

	targetPath.push(target.pathPrefix);
	targetPath.unshift(__dirname);
	targetPath.push(exec);

	return path.join.apply(__dirname, targetPath);
}

exports.path = getPathToPythonScript(target);

