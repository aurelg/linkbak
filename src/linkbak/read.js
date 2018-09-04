// npm install fs
const fs = require("fs");
// npm install jsdom
const jsdom = require("jsdom");
const { JSDOM } = jsdom;
// npm install https://github.com/mozilla/readability
const Readability = require("readability");

fs.readFile("index.dom", function(err, data) {
  const dom = new JSDOM(data);
  const article = new Readability(dom.window.document).parse();
  console.log(article.content);
  // if (err) throw err;
});
