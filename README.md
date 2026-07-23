# Iceberg_Hash

Project 3 of 3 in my quest to make a more robust hash algorithm.

## What it does

Uses double hashing on a front and back yard to create a hash that's capable of holding around 95% capacity. Distribution should be very consistent because, instead of the random placement into buckets you get with cuckoo hashing, I give the hash the choice based on which bucket contains fewer elements, similar to robinhood hashing.

If both front yard buckets a key hashes to are full, the item is re-hashed with a different seed and placed in the backyard. The backyard is very small because the power of choice logic keeps it from filling up often.

There's still a tiny chance of failure if both front-yard buckets *and* both backyard buckets a key routes to are all full. The odds are so small (again, power of two choices) that I'm not worried about it.

The table resizes based on **backyard usage**, because the backyard is the real indicator that hashing is starting to fail. Using a backyard makes it more space efficient but less time efficient — before an item lands in a backyard bucket, its key has to be compared against both of its front-yard hash locations.

## Files

- `iceberg.py` — the working v1. Mod-based bucket indexing, list-of-lists storage.
- `faster_iceberg_v2.py` — same logic, but bucket counts are rounded to a power of 2 so I can use bitwise AND instead of mod, and resize copies through a numpy array.
- `faster_iceberg.py` — **WIP**. My attempt at moving from array-of-structs to struct-of-arrays and using 1-byte fingerprints so a lookup can scan a whole cache line at once. `_find_key` isn't finished and there are still a few typos in it — leaving it here as a snapshot of where I stopped.

## Requirements

- Python 3.10+ (uses `match` statements and `TypeAlias`)
- `mmh3`
- `numpy` (for the faster versions)

## Usage

```python
from iceberg import IcebergHash

h = IcebergHash(capacity=2048)
h["key"] = "value"
h[42] = 420
print(h["key"])     # "value"
h.delete("key")
```

Keys can be `str` or `int`.

## Reflection

Out of the 3 small projects I did, I liked the cuckoo filter most. It may be less efficient than iceberg (even though they aren't really comparable), but I really liked the XOR logic with fingerprints that lets keys hold 2 values. The filter was so space efficient that time efficiency stopped being a tradeoff. The whole filter array was compact enough to fit in my L1 cache. A cache miss typically results in around 100 missed cpu cycles which allows a dumb algorithm that is able to use highly compressed data (cuckoo filter) to compete or even outperform algorithms with much fewer operations but poor cache locality.

To be honest, my goal starting these projects was to understand iceberg hashing, but I'm way more proud of my cuckoo filter and I learned way more building it. All the byte and bit comparisons made me miss C.

I didn't bother learning how the time complexity is proven for iceberg — the proofs seemed pretty intimidating. I read a little over 10 pages of [Mitzenmacher's handbook chapter](https://www.eecs.harvard.edu/~michaelm/postscripts/handbook2001.pdf) on it. I understand the power of choice pretty well, but not the math behind it.


