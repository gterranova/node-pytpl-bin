# node-pyserver-bin 

[pyserver](http://github.com/gterranova/node-pyserver-bin) 0.1.0 Node.js wrapper that makes a basic python server seamlessly available as a local dependency.

> pyserver is python webserver for locally testing and running cgi application written in python.

## Install

Install with npm: `npm install --save git://github.com/gterranova/node-pyserver-bin.git`


## Example usage

```js
var execFile = require('child_process').execFile;
var pyserverPath = require('node-pyserver-bin').path;

execFile(pyserverPath, ['-v'], function(err, stdout, stderr) {
console.log('pyserver running');
});
```

Can also be run directly from `./node_modules/.bin/pyserver`.


## License

Everything licensed under the [BSD license](http://opensource.org/licenses/bsd-license.php)  and copyright Gianpaolo Terranova.

