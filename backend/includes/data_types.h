// -*- mode: c++; c-file-style: "k&r"; c-basic-offset: 4 -*-
// vim: set ts=4 sw=4:
/***********************************************************************
 *
 * includes/data_types.h
 *   Diamond data type definitions
 *
 **********************************************************************/

#ifndef _DATA_TYPES_H_
#define _DATA_TYPES_H_

#include <unordered_set>

namespace diamond {

class DString
{
public:
    DString() {};
    DString(const std::string &s, const std::string &key) : _s(s) {};
    ~DString() {};
    static int Map(DString &addr, const std::string &key);
    std::string Value();
    void Set(const std::string &s);
    DString & operator=(const std::string &s) { Set(s); return *this; };
        
private:
    std::string _s;
    std::string _key;
};
    
class DLong
{
public:
    DLong() {};
    DLong(const uint64_t l, const std::string &key) : _l(l), _key(key) {};
    ~DLong() {};
    static int Map(DLong &addr, const std::string &key);
    uint64_t Value();
    void Set(const uint64_t l);
    DLong & operator=(const uint64_t l) { Set(l); return *this; };
    DLong & operator+=(const uint64_t i) { Set(_l + i); return *this; };
    DLong & operator-=(const uint64_t i) { Set(_l - i); return *this; };
    
private:
    uint64_t _l;
    std::string _key;
};


class DCounter
{
public:
    DCounter() {};
    DCounter(const int c, const std::string &key) : _counter(c), _key(key) {};
    ~DCounter() {};
    static int Map(DCounter &addr, const std::string &key);
    int Value();
    void Set(const int val);
    DCounter & operator=(const int val) { Set(val); return *this; };
    DCounter operator++() { Set(_counter + 1); return *this; };
    DCounter operator--() { Set(_counter - 1); return *this; };
    DCounter & operator+=(const uint64_t i) { Set(_counter + i); return *this; };
    DCounter & operator-=(const uint64_t i) { Set(_counter - i); return *this; };

private:
    int _counter;
    std::string _key;
    
};

class DSet
{
public:
    DSet() {};
    DSet(std::unordered_set<uint64_t> set, const std::string &key) : _key(key), _set(set) {};
    ~DSet() {};
    static int Map(DSet &addr, const std::string &key);
    std::unordered_set<uint64_t> Members();
    bool InSet(const uint64_t val);
    void Add(const uint64_t val);
    void Add(const std::unordered_set<uint64_t> &set);
    void Remove(const uint64_t val);
    DSet & operator=(const std::unordered_set<uint64_t> &set) { Add(set); return *this; };
    
private:
    std::string _key;
    std::unordered_set<uint64_t> _set;

    std::string Serialize();
    void Deserialize(std::string &s);
};

} // namespace diamond

#endif 