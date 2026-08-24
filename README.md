# Iceberg_Hash
developed locally, uploaded on completion

Project 3 of 3 in my quest to make a more robust hash algorithm.

## What it does

calculates 2 hashes and puts to the hashed bucket with a lower capacity  with a seperate buffer for overflow, creating a hash table that's capable of holding around 95% capacity. Distribution should be very consistent because, instead of the random selection with swaps you get with cuckoo hashing, the algorithm is able to utilize the [power of two choices](https://www.eecs.harvard.edu/~michaelm/postscripts/handbook2001.pdf) to choose the bucket contains fewer elements, similar to robinhood hashing which uses linear probing with the twist of evicting the value closer to its true hash location to create balance.

If both front yard buckets are full, the item is rehashed with a different seed and placed in the backyard. Unlike an actual literal iceberg in the ocean, the part that stays hidden or refered to as the "backyard" for iceberg hashing is very small because the power of two choice keeps the buckets in the frontyard balanced resulting in improbable overflow even at extremely high load factors for open addressing. 

There's still a tiny chance of failure if both frontyard buckets *and* both backyard buckets a key routes to are all full. The odds are so small (again, power of two choices) that I'm not worried about it.

The table resizes based on **backyard usage**, because the backyard is the real indicator that hashing is starting to fail. Using a backyard makes it more space efficient but less time efficient — before an item lands in a backyard bucket, its key has to be compared against both of its frontyard hash locations.

## Files

- `iceberg.py` — the working v1. Mod based bucket indexing, list of lists storage.
- `faster_iceberg_v2.py` — same logic, but bucket counts are rounded to a power of 2 so I can use bitwise AND instead of mod, and resize copies through a numpy array.
- `faster_iceberg.py` — **WIP**. My attempt at moving from array of structs to struct of arrays and using 1 byte fingerprints so a lookup can scan a whole cache line at once. `_find_key` isn't finished and there are still a few typos in it — leaving it here as a snapshot of where I stopped.

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

Out of the 3 small projects I did, I liked the cuckoo filter most. It may be less efficient than iceberg (even though they aren't really comparable), but I really liked the XOR logic with fingerprints that lets keys hold 2 values. The filter was so space efficient that time efficiency stopped being a tradeoff. The whole filter array was compact enough to fit in my L1 cache. A cache miss resulting in ram lookup typically results in 100+ missed cpu cycles which allows a dumb algorithm that is able to use highly compressed data (cuckoo filter) to compete or even outperform algorithms with much fewer operations but poor cache locality.

To be honest, my goal starting these projects was to understand iceberg hashing, but I'm way more proud of my cuckoo filter and I learned way more building it. All the byte and bit comparisons made me miss C.

I didn't bother learning how the time complexity is proven for iceberg, the proofs seemed pretty intimidating. I read a little over 10 pages of [Mitzenmacher's handbook chapter](https://www.eecs.harvard.edu/~michaelm/postscripts/handbook2001.pdf) on it. I understand the power of choice pretty well, but not the math behind it.

-------------------------------------------------------------------------------
Thought process

I might need to try using the power of choice with a separate chaining hash sometime. If the head node held length and end-of-chain metadata, I could see iceberg being an excellent approach to minimize clusters for improved lookup. The chains will be sorted by the bits of the hash value in reverse ordering to save computation on resize.

Ex.
Start at buffer size 2 — Example: chain A: 10001 < 00011 < 10011 < 11111; chain B: 10000 < 00010 < 10010 < 11110
Resize to buffer size 4 — chain A: 10001; chain B: 10000; chain C: 00011 < 10011 < 11111; chain D: 00010 < 10010 < 11110

Conclusion
As you can see, as long as ordering is preserved from putting, once the first node to move is found the rest will follow, and the new linked list at that location is already organized. Since the buffer is sized by 2^x, a resize will simply mean one more bit is being read from the hash to find the slot the value belongs in. For the first instance in a chain of a value that needs to move, all following values would also need to be moved. 

After resize, the chains will start uneven, but the power of choice should balance things out. Theres probably a reson I cant find anyone doing a single layor with chaining on google scholar, I'll look more into it later.


