import { test } from 'node:test';
import assert from 'node:assert/strict';
import { shuffleChoices } from '../src/lib/shuffle.ts';

test('all six three-option permutations are reachable without favoring a correct position', () => {
  const choices = Object.freeze([{ id: 'answer', text: 'Correct text' }, { id: 'b', text: 'Other B' }, { id: 'c', text: 'Other C' }].map(option => Object.freeze(option)));
  const orders = new Set<string>(), positions = [0, 0, 0];
  for (let first = 0; first < 3; first++) for (let second = 0; second < 2; second++) {
    const draws = [(first + .5) / 3, (second + .5) / 2];
    const shuffled = shuffleChoices(choices, () => draws.shift()!);
    orders.add(shuffled.map(o => o.id).join(','));
    positions[shuffled.findIndex(o => o.id === 'answer')]++;
    assert.deepEqual(new Set(shuffled), new Set(choices));
    for (const option of shuffled) assert.strictEqual(option, choices.find(o => o.id === option.id));
  }
  assert.equal(orders.size, 6);
  assert.deepEqual(positions, [2, 2, 2]);
  assert.deepEqual(choices.map(o => o.id), ['answer', 'b', 'c']);
});

test('fresh shuffles use fresh draws; empty and single-choice inputs stay valid', () => {
  assert.deepEqual(shuffleChoices([], () => { throw new Error('No draw required'); }), []);
  assert.deepEqual(shuffleChoices(['only'], () => { throw new Error('No draw required'); }), ['only']);
  const input = ['a', 'b', 'c'];
  assert.notDeepEqual(shuffleChoices(input, () => 0), shuffleChoices(input, () => .99));
  assert.deepEqual(input, ['a', 'b', 'c']);
});
