from __future__ import annotations
import math

from typing import Generic, TypeVar, TypeAlias
from dataclasses import dataclass
import mmh3
"""
Uses double hashing on a front and back yard to create a hash that is capaable of holding around 95% cap. 
the distribution should be very consistent because instead of random placement in buckets of double hashing in cuckoo we give the hash the choice based on which contains less elements like in robinhood hashing.
if both buckets a value is hash too is full the item recalculates using a different seed and is placed in the backyard which is very small because the ability to choose. 
This hashing function still has a tiny chance of crashing in the case both the front yard buckets are full and both of the backyard buckets the key routes to are also full. although the chances of this happening are so small because of the power of 2 choices im not worried.
The hash resizes based on backyard usage, because the backyard is the real indicator that hashing is failing. because I used backyard my alg is more space efficient but less time efficient because before an item gets filled in a back bucket the key needs to be compared with both of its coresponding hash locations in the front yard.
Out of the 3 small project I did I liked the cuckoo filter most. It may be less efficient then iceberg even though they arnt comparable, but I really liked the xor logic with fingerprints to get keys to hold 2 values. The filter was so space efficient time efficiency no longer became a tradeoff because the entire filter array was so compress it fit on my l1 cache. 
To be honest my goal when starting my projects was to understand iceberg hashing but I'm way more proud of my cuckoo filter and I learned way more while constructing it. All the byte and bit comparisons I did made me miss C.
I didnt bother learning how the timecomplexity was proven for this because the proofs seemed pretty intimidating. I read a little over 10 pages of https://www.eecs.harvard.edu/~michaelm/postscripts/handbook2001.pdf explaining it.
I understand the power of choice pretty well but not the math behind it. Because I really like tye bit operations for cuckoo I'm gonna try to get some extra time next weekend to work on swiss tables because they seem to have a few overlapping elements.
"""

T = TypeVar('T')

@dataclass
class Some(Generic[T]):
    value: T

@dataclass
class NoneOption():
    pass

OptionT: TypeAlias= Some[T]| NoneOption


class IcebergHash:
    def __init__(self, capacity:int = 2048, bucket_size:int = 8):#not updated to use bitwise operations
        """
        backyard need n/logn slots aprox 5%
        it would be cool if py supported 4bit datatypes so i could have bucket_size static at 8 and my f_buff_status would be an array of 4 bit slots
        """
        self.bucket_size = bucket_size
        self.back_yard_buckets = math.ceil(capacity/math.log(capacity))//bucket_size
        self.front_yard_buckets = capacity//bucket_size
        self.f_buff = [[NoneOption()]*bucket_size for _ in range(self.front_yard_buckets)]
        self.b_buff = [[NoneOption()]*bucket_size for _ in range(self.back_yard_buckets)]
        self.f_status = [0 for _ in range(self.front_yard_buckets)]
        self.b_status = [0 for _ in range(self.back_yard_buckets)]
        self.back_yard_items = 0
    
    def _hash_front_yard(self, hash_input):
        """
        I plan on refining the input to reduce hash iterations once I get a working version
        """
        optA, optB = mmh3.hash64(hash_input, seed = 42, signed = False)
        return optA%self.front_yard_buckets, optB%self.front_yard_buckets
    
    def _hash_back_yard(self, hash_input):
        optA, optB = mmh3.hash64(hash_input, seed = 0, signed = False)
        return optA%self.back_yard_buckets, optB%self.back_yard_buckets
    
    @staticmethod
    def _key_convert(key):
        match key:
            case str():
                return key.encode()
            case int():
                return key.to_bytes(8, "big")
 
    def _find_key(self, bucket, key, status)->int:
        """
        returns index of key or -1 if not found 
        """

        key_idx = -1
        for i in range(self.bucket_size):
            if status<1:
                break
            if bucket[i]==NoneOption():
                pass
            else:
                status-=1
                if bucket[i][0].value==key:
                    return i
        return key_idx
    
    def _empty_slot(self, bucket)->int:
        """
        returns index of key or first found empty 
        """
        for i in range(self.bucket_size):
            if isinstance(bucket[i],NoneOption):
                return i
        raise IndexError("cant find NoneOption in bucket")# should never happen
    
    def _gen_candidates(self, idxs):
        return [
            (self.f_buff, self.f_status, idxs[0]),
            (self.f_buff, self.f_status, idxs[1]),
            (self.b_buff, self.b_status, idxs[2]),
            (self.b_buff, self.b_status, idxs[3])
        ]

    def insert(self, key, value):
        idx1, idx2 = self._hash_front_yard(self._key_convert(key))
        idx3, idx4 = self._hash_back_yard(self._key_convert(key))

        c = self._gen_candidates([idx1, idx2, idx3, idx4])
        
        for b, s, i in c:
            result = self._find_key(b[i], key, s[i])#checking for existing identical keys
            if result>-1:
                b[i][result] = (Some(key), Some(value))
                return True

        if self.f_status[idx1]!= self.bucket_size or self.f_status[idx2]!=self.bucket_size:
            if self.f_status[idx1]<self.f_status[idx2]:
                self.f_buff[idx1][self._empty_slot(self.f_buff[idx1])] = (Some(key), Some(value))
                self.f_status[idx1]+=1
                return True
            else:
                self.f_buff[idx2][self._empty_slot(self.f_buff[idx2])] = (Some(key), Some(value))
                self.f_status[idx2]+=1
                return True
        

        #not going to bother catching if both backyards are full because its rare and i have a error that raises in emptyslot
        if self.b_status[idx3]<self.b_status[idx4]:
            self.b_buff[idx3][self._empty_slot(self.b_buff[idx3])] = (Some(key), Some(value))
            self.b_status[idx3]+=1
        else:
            self.b_buff[idx4][self._empty_slot(self.b_buff[idx4])] = (Some(key), Some(value))
            self.b_status[idx4]+=1
        
        self.back_yard_items+=1
        if self.back_yard_items/(self.bucket_size*self.back_yard_buckets)>.5:
            self.resize()
        return True
    
    def __setitem__(self, key,  value):
        return self.insert(key, value)
    
    def blind_insert(self, key, val):
        """
        inserts without checking for duplicate keys
        faster in cases we dont need to check duplicate keys and dosnt run into the risk of resize triggering while resize is running
        """
        idx1, idx2 = self._hash_front_yard(self._key_convert(key))
        idx3, idx4 = self._hash_back_yard(self._key_convert(key))
        
        if self.f_status[idx1]!=self.bucket_size or self.f_status[idx2]!=self.bucket_size:
            if self.f_status[idx1]<self.f_status[idx2]:
                t_ind = self._empty_slot(self.f_buff[idx1])
                self.f_buff[idx1][t_ind] = (Some(key), Some(val))
                self.f_status[idx1]+=1
            else:
                t_ind = self._empty_slot(self.f_buff[idx2])
                self.f_buff[idx2][t_ind]= (Some(key), Some(val))
                self.f_status[idx2]+=1
        else:
            if self.b_status[idx3]<self.b_status[idx4]:
                t_ind = self._empty_slot(self.b_buff[idx3])
                self.b_buff[idx3][t_ind] = (Some(key),Some(val))
                self.b_status[idx3]+=1
                self.back_yard_items+=1
            else:
                t_ind = self._empty_slot(self.b_buff[idx4])
                self.b_buff[idx4][t_ind] =(Some(key), Some(val))
                self.b_status[idx4]+=1
                self.back_yard_items+=1
        return True



    def resize(self):
        old_f , old_b = self.f_buff, self.b_buff
        new_capacity = self.front_yard_buckets*self.bucket_size*2
        self.__init__(capacity=new_capacity, bucket_size=self.bucket_size)

        for b in old_f:
            for s in b:
                if not isinstance(s, NoneOption):
                    self.blind_insert(s[0].value, s[1].value)
        for b in old_b:
            for s in b:
                if not isinstance(s, NoneOption):
                    self.blind_insert(s[0].value, s[1].value)
        
    
    def __getitem__(self, key):
        idx1, idx2 = self._hash_front_yard(self._key_convert(key))
        idx3, idx4 = self._hash_back_yard(self._key_convert(key))
        c = self._gen_candidates([idx1, idx2, idx3, idx4])
        for b, s, i in c:
            result = self._find_key(b[i], key, s[i])
            if result>-1:
                return b[i][result][1].value
        return None
    
    def delete(self, key)->bool:
        idx1, idx2 = self._hash_front_yard(self._key_convert(key))
        idx3, idx4 = self._hash_back_yard(self._key_convert(key))
        c = self._gen_candidates([idx1,idx2,idx3,idx4])
        for b, s, i in c:
            result = self._find_key(b[i], key, s[i])
            if result>-1:
                s[i]-=1
                b[i][result]=NoneOption()
                if b is c[2][0] or b is c[3][0]:
                    self.back_yard_items-=1
                return True
        return False

            



    

            

