import test from 'node:test';
import assert from 'node:assert/strict';
import {CandidatePlayback,recipe} from './playback.mjs';
test('sleep remains asleep until wake, exits at the cycle seam and returns to BASE',()=>{
 const p=new CandidatePlayback(recipe('M061','SLEEP'));
 p.advance(1820); assert.equal(p.phase,'hold'); assert.equal(p.sample(),5);
 p.advance(3600*4); assert.equal(p.phase,'hold');
 p.advance(600);p.wake();assert.equal(p.phase,'hold');
 p.advance(2999);assert.equal(p.phase,'hold');p.advance(1);assert.equal(p.phase,'exit');assert.equal(p.sample(),9);
 p.advance(1100);assert.equal(p.phase,'done');assert.equal(p.sample(),11);
});
test('early wake request completes entry and a hold cycle before exit',()=>{
 const p=new CandidatePlayback(recipe('M061','SLEEP'));p.wake();p.advance(1820);assert.equal(p.phase,'hold');
 p.advance(3600);assert.equal(p.phase,'exit');
});
test('defeat never wraps to standing frame, even over a long elapsed interval',()=>{
 for(const m of ['M061','M062','M064']){
  const p=new CandidatePlayback(recipe(m,'DEFEAT'));p.advance(60000);assert.equal(p.phase,'held');assert.equal(p.sample(),11);
  p.wake();p.advance(60000);assert.equal(p.phase,'held');
 }
});
test('attack is one shot; frame duration controls anticipation and strike',()=>{
 const p=new CandidatePlayback(recipe('M062','ATTACK'));p.advance(619);assert.equal(p.sample(),3);
 p.advance(1);assert.equal(p.sample(),4);p.advance(80);assert.equal(p.sample(),5);
 p.advance(10000);assert.equal(p.phase,'done');assert.equal(p.sample(),11);
});
test('propulsion repeats without inserting a hold',()=>{
 const r=recipe('M061','MOVE'),p=new CandidatePlayback(r);
 const duration=r.phases.stroke.frames.reduce((s,f)=>s+f.ms,0);
 p.advance(duration);assert.equal(p.sample(),0);assert.equal(p.phase,'stroke');
});
test('failed and identity-blocked candidates have no recipe',()=>{
 for(const m of ['M062','M063','M065'])assert.throws(()=>recipe(m,'MOVE'));
 assert.throws(()=>recipe('M064','ATTACK'));
});
test('invalid elapsed time is rejected without changing state',()=>{
 const p=new CandidatePlayback(recipe('M061','MOVE'));
 for(const n of [-1,NaN,Infinity])assert.throws(()=>p.advance(n));assert.equal(p.sample(),0);
});
