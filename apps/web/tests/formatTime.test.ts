import test from 'node:test';
import assert from 'node:assert/strict';
import { formatBeijingTime, utcTimestamp } from '../src/lib/formatTime.ts';

test('UTC database timestamps display Beijing time without milliseconds', () => {
  assert.equal(formatBeijingTime('2026-10-23T10:16:16.637'), '2026-10-23 18:16:16');
  assert.equal(formatBeijingTime('2026-10-23T10:16:16.637Z'), '2026-10-23 18:16:16');
  assert.equal(formatBeijingTime('2026-10-23T18:16:16+08:00'), '2026-10-23 18:16:16');
});
test('Beijing day/year rollover and midnight use zero-padded 24-hour time', () => {
  assert.equal(formatBeijingTime('2026-10-23T16:00:00'), '2026-10-24 00:00:00');
  assert.equal(formatBeijingTime('2026-12-31T23:01:02Z'), '2027-01-01 07:01:02');
  assert.equal(utcTimestamp('2026-10-23T10:16:16Z'), '2026-10-23T10:16:16Z');
  assert.equal(formatBeijingTime('invalid'), '时间未知');
});
