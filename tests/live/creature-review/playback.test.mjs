import test from 'node:test';
import assert from 'node:assert/strict';
import {reviewPlayback} from './playback.mjs';
const make=action=>reviewPlayback(`/design/production-batches/luma-asset-16/M061/${action}-candidate/rigged/${action}`,12);
const run=(p,ms)=>{for(let i=0;i<ms;i+=10)p.advance(10,false,false);};
test('sleep holds until wake boundary, exits to base',()=>{const p=make('sleep');run(p,1820);assert.equal(p.phase,'hold');run(p,3600);assert.equal(p.phase,'hold');p.wake();run(p,3590);assert.equal(p.phase,'hold');run(p,10);assert.equal(p.phase,'exit');run(p,1100);assert.equal(p.base,true);});
test('defeat terminal, attack base, move repeats',()=>{const d=make('defeat'),a=make('attack'),m=make('move');run(d,10000);assert.equal(d.phase,'held');assert.equal(d.base,false);run(a,10000);assert.equal(a.base,true);run(m,10000);assert.equal(m.phase,'stroke');});
test('pause reduced motion selection and resume preserve state',()=>{const p=make('sleep');p.advance(100,true,false);p.advance(100,false,true);assert.equal(p.player.elapsed,0);p.select(8);run(p,1000);assert.equal(p.sample(),8);assert.equal(p.player.elapsed,0);p.resume();run(p,240);assert.equal(p.sample(),1);p.restart();assert.equal(p.sample(),0);});
test('recipes cannot leak to other versions or incomplete deliveries',()=>{assert.equal(reviewPlayback('/design/other/M061/sleep',12),null);assert.equal(reviewPlayback('/design/production-batches/luma-asset-16/M061/sleep-candidate/rigged/sleep',8),null);});
