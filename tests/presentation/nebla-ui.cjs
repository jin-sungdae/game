const {test}=require('node:test');const assert=require('node:assert/strict');const path=require('node:path');
const React=require('react');const {renderToStaticMarkup}=require('react-dom/server');
const {CompanionVisual}=require(path.join(process.env.LUMA_PRESENTATION_TEST_DIR,'components/CompanionVisual.js'));
test('unsupplied Stage3 renders NEBLA diagnostic without another stage image',()=>{
 const html=renderToStaticMarkup(React.createElement(CompanionVisual,{species:'moa',evolutionStage:3,state:'IDLE',facing:1}));
 assert.match(html,/NEBLA/);assert.match(html,/Stage 3 · asset pending/);
 assert.doesNotMatch(html,/<img|MOKORI|stage02|stage01/);
});
