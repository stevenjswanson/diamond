// -*- mode: c++; c-file-style: "k&r"; c-basic-offset: 4 -*-
// vim: set ts=4 sw=4:
/***********************************************************************
 *
 * data_types/Counter.cc
 *   Diamond counter type
 *
 **********************************************************************/

#include "storage/cloud.h"
#include "includes/data_types.h"
#include "lib/assert.h"
#include "lib/message.h"
#include <unordered_map>

namespace diamond {

using namespace std;

static unordered_map<string, DCounter> cache;

int
DCounter::Map(DCounter &addr, const string &key) {

    addr._key = key;
    // take a look in the cache first
    auto find = cache.find(key);
    if (find != cache.end()) {
        addr._counter = find->second._counter;
        return ERR_OK;
    }
   
   if (!cloudstore->IsConnected()) {
      Panic("Cannot map objects before connecting to backing store server");
   }

   string value;
   
   int ret = cloudstore->Read(key, value);

   if (ret != ERR_OK) {
      return ret;
   }

   addr._counter = atol(value.c_str());
   cache[key] = addr;
   return 0;
}

int
DCounter::Value() {
    string s;
    int ret = cloudstore->Read(_key, s);

    if (ret == ERR_OK) {
        _counter = atoi(s.c_str());
    }
    return _counter;
}
        
void
DCounter::Set(int val)
{
    _counter = val;
    char buf[50];
    sprintf(buf, "%i", _counter);
    cloudstore->Write(_key, string(buf));
}
   
} // namespace diamond
