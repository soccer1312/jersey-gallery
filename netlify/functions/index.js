// This file helps Netlify recognize the functions directory
// The actual functions are in the api and proxy-image subdirectories
module.exports = {
  api: require('./api/index.py'),
  'proxy-image': require('./proxy-image/index.py')
}; 