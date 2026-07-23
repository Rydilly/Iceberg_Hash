from __future__ import annotations
import math
import numpy as np
from typing import Generic, TypeVar, TypeAlias
from dataclasses import dataclass
import mmh3
"""
only speeding up the resize by using a np array
"""

T = TypeVar('T')

@dataclass
class Some(Generic[T]):
    value: T

@dataclass
class NoneOption():
    pass

OptionT: TypeAlias= Some[T]| NoneOption
#RESIZE STILL NEEDS WORK LOL TO ARRAY MAKES NMPY ANGRY

class IcebergHash:
    def __init__(self, capacity:int = 2048, bucket_size:int = 8):
        """
        backyard need n/logn slots aprox 5%
        it would be cool if py supported 4bit datatypes so i could have bucket_size static at 8 and my f_buff_status would be an array of 4 bit slots
        """
        self.bucket_size = bucket_size
        self.back_yard_buckets = 1<<self._log_calc(math.ceil(capacity/math.log(capacity))//bucket_size)
        self.front_yard_buckets = 1<<self._log_calc(capacity//bucket_size)
        self.f_buff = [[NoneOption()]*bucket_size for _ in range(self.front_yard_buckets)]
        self.b_buff = [[NoneOption()]*bucket_size for _ in range(self.back_yard_buckets)]
        self.f_status = [0 for _ in range(self.front_yard_buckets)]
        self.b_status = [0 for _ in range(self.back_yard_buckets)]
        self.back_yard_items = 0
    
    @staticmethod
    def _log_calc(n):
        #converst n to a clean power of 2
        if n <2:
            return 0
        p = 0
        n = n-1
        while n >0:
            p+=1
            n>>=1
        return p
    
    def _hash_front_yard(self, hash_input):
        """
        I plan on refining the input to reduce hash iterations once I get a working version
        """
        optA, optB = mmh3.hash64(hash_input, seed = 42, signed = False)
        return optA&(self.front_yard_buckets-1), optB&(self.front_yard_buckets-1)#bitwise is faster then mod
    
    def _hash_back_yard(self, hash_input):
        optA, optB = mmh3.hash64(hash_input, seed = 0, signed = False)
        return optA&(self.back_yard_buckets-1), optB&(self.back_yard_buckets-1)
    
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
    
    def __setitem__(self, key, value):
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
        old_f , old_b = np.array(self.f_buff), np.array(self.b_buff)
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

 