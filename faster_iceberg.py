from __future__ import annotations
import math
import numpy as np
from typing import Generic, TypeVar, TypeAlias
from dataclasses import dataclass
import mmh3

"""
TO-DO:
numpy array for rehashing on resize
numpy uint8 for fingerprint to search through buckets quicker
on resize hash np.uint64 array
bitwise operation rather than mod
for shift hash>>old log &1
"""

OptionT: TypeAlias= Some[T]| NoneOption

class IcebergHash:
    def __init__(self, capacity:int = 2000, bucket_size:int = 8):
        """
        backyard need n/logn slots aprox 5%
        it would be cool if py supported 4bit datatypes so i could have bucket_size static at 8 and my f_buff_status would be an array of 4 bit slots
        """
        bucket_size = 8#with my new version i want a bucket to be only 8 byte because when i use fingerprints to speed up find each bucket will have a 1 byte fingerprint meaning i could get a 64 byte cache line for 2 front 2 back yard buckets

        #redundent but might be needed later
        self.bucket_size = 1<<self._log_size(bucket_size)#ensure cap is a power of 2 so we can use bitwise rather then mod
        back_yard_log = self._log_size(math.ceil(capacity/math.log(capacity))//self.bucket_size)
        self.back_yard_buckets = 1<<back_yard_log
        

        front_yard_log = self._log_size(capacity//self.bucket_size)
        self.front_yard_buckets = 1<<front_yard_log
        

        #hash table is converted from an Array of structures to a structure of arrays to assess fingerprints on singly cache line
        f_slots = self.front_yard_buckets*self.bucket_size#note status is gone. Fingerprint should be so fast to search slots is no longer needed
        self.f_f = np.zeros(f_slots, dtype=np.uint8)#front yard fingerprints
        self.f_hash = np.zeros(f_slots, dtype = np.uint64)
        self.f_keys = [None]*f_slots
        self.f_values = [None]*f_slots
        
        b_slots = self.b_slots*self.bucket_size
        self.b_f = np.zeros(b_slots, dtype = np.unit8)
        self.b_hash = np.zeros(b_slots, dtype = np.unit64)
        self.b_keys = [None]*b_slots#np arrays would just add overhead for conversion
        self.b_values = [None]*b_slots

        self.back_yard_items = 0

    @staticmethod
    def _log_size(capacity):
        if capacity<2:
            return 0
        n = capacity-1
        result = 0
        while n:
            n>>=1
            result+=1
        return result

    """
                        NEED TO REFACTOR EVERYTHING THAT RECEIVES FRONT YARD FINGER
    """
    def _hash_front_yard(self, hash_input):
        """
        I plan on refining the input to reduce hash iterations once I get a working version
        """
        optA, optB = mmh3.hash64(hash_input, seed = 42, signed = False)
        cmp = self.front_yard_buckets-1#remember front yard buckets is an exponent of 2, so fy-1= 111....
        finger_hash = mmh3(hash_input, seed= 69, signed = False)#front yard will always be called, so we make the fingerprint here
        return optA&cmp, optB&cmp, finger_hash&0xFF#last 2 are fingerprints. F is 15 in hex (1111), so FF is a byte of all 1s
    
    def _hash_back_yard(self, hash_input):
        optA, optB = mmh3.hash64(hash_input, seed = 0, signed = False)
        cmp = self.back_yard_buckets-1#byb is also an exponent of 2
        return optA&cmp, optB&cmp
    
    @staticmethod
    def _key_convert(key):
        match key:
            case str():#could add first 2 last 2 char as key or reference an array if 1 char
                return key.encode()
            case int():
                return key.to_bytes(8, "big")
 
    def _find_key(self, key)->int:
        """
        returns index of key or -1 if not found 
        """
        idx1, idx2, fp = self._hash_front_yard(key)
        idx3, id4 =self._hash_back_yard(key)#hash both to get 64byte fp array
        key_idx = None

        fp_array = self.f_f[idx1]+self.f_f[idx2]+self.b_f[idx3]+self.b_f[id4]
        for i in np.where(fp_array==fp):
            if self.f_keys[i]
        #somehow check fp array for fp



        #if cant fint in fy...
        self._hash_back_yard(key)
    
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
        idx1, idx2, finger_print = self._hash_front_yard(self._key_convert(key))
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
        old_f , old_b = np.array(self.f_buff), np.array(self.b_buff)#benchmark this feature
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
        
    
    def get(self, key):
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

            
if __name__=="__main__":
    I = IcebergHash(capacity=2048)
    for i in range(100):
        I.insert(i, i*10)
    assert sum(I.f_status)+sum(I.b_status)==100

    for i in range(100):#get works
        assert I.get(i)==i*10

    for i in range (0,100,2):
        assert I.delete(i) == True

    assert sum(I.f_status)+sum(I.b_status)==50

    for i in range(0,100,2):
        assert I.get(i) == None

    for i in range(1,100,2):
        assert I.get(i) == i*10

    assert I.delete(999) is False

    ht = IcebergHash(capacity=128)
    n = 200
    for i in range(n):
        ht.insert(i, i*10)

    # resize must have fired by now (capacity=128, ~16 backyard slots, 50% threshold = ~8 items in backyard)
    for i in range(n):
        assert ht.get(i) == i*10, f"lost key {i} after resize"

    print("resize ok")


    

            

