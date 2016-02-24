// -*- mode: c++; c-file-style: "k&r"; c-basic-offset: 4 -*-
// vim: set ts=4 sw=4:
/***********************************************************************
 *
 * client/diamondclient.cc:
 *   Client to Diamond frontend servers
 *
 * Copyright 2016 Irene Zhang <iyzhang@cs.washington.edu>
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use, copy,
 * modify, merge, publish, distribute, sublicense, and/or sell copies
 * of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
 * BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
 * ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 **********************************************************************/

#include "diamondclient.h"

namespace diamond {

using namespace std;

thread_local uint64_t txnid = 0;
thread_local Transaction txn;

DiamondClient::DiamondClient(string configPath)
    : transport()
{
    // Initialize all state here;
    client_id = 0;
    while (client_id == 0) {
        random_device rd;
        mt19937_64 gen(rd());
        uniform_int_distribution<uint64_t> dis;
        client_id = dis(gen);
    }
    txnid_counter = (client_id/10000)*10000;
    last_reactive = Timestamp(0);

    Debug("Initializing Diamond Store client with id [%lu]", client_id);

    /* Start a client for the front-end. */
    frontend::Client *frontendclient = new frontend::Client(configPath + ".config",
                                                            &transport,
                                                            client_id);
    client = new ReactiveClient(frontendclient);

    /* Run the transport in a new thread. */
    clientTransport = new thread(&DiamondClient::run_client, this);

    Debug("Diamond Store client [%lu] created!", client_id);
}

DiamondClient::~DiamondClient()
{
    transport.Stop();
    clientTransport->join();
}

/* Runs the transport event loop. */
void
DiamondClient::run_client()
{
    transport.Run();
}
    
/* Begins a transaction. All subsequent operations before a commit() or
 * abort() are part of this transaction.
 */
void
DiamondClient::Begin()
{
    if (txnid == 0) {
        Debug("Diamondclient::BEGIN Transaction");
        txnid_lock.lock();
        txnid = ++txnid_counter;
        txnid_lock.unlock();
        txn = Transaction(LINEARIZABLE);
        client->Begin(txnid);
    }
}

void
DiamondClient::BeginRO()
{
    if (txnid == 0) {
        Debug("Diamondclient::BEGIN Transaction");
        txnid_lock.lock();
        txnid = ++txnid_counter;
        txnid_lock.unlock();
        txn = Transaction(READ_ONLY);
        client->BeginRO(txnid);
    }
}

void
DiamondClient::BeginReactive(uint64_t reactive_id)
{
    if (txnid == 0) {
        Debug("Diamondclient::BEGIN_REACTIVE Transaction");
        txnid_lock.lock();
        txnid = ++txnid_counter;
        txnid_lock.unlock();
       
        Timestamp timestamp = last_reactive;
        timestamp_map_lock.lock();
        if (timestamp_map.find(reactive_id) != timestamp_map.end()) {
            timestamp = timestamp_map[reactive_id];
        }
        timestamp_map_lock.unlock();

        txn = Transaction(READ_ONLY, timestamp, reactive_id);
        client->BeginRO(txnid);
    }
}

/* Returns the value corresponding to the supplied key. */
int
DiamondClient::Get(const string &key, string &value)
{
    if (txnid == 0) {
        Panic("Doing a GET outside a transaction. YOU ARE A BAD PERSON!!");
    }
    
    Debug("GET [%lu] %s", txnid, key.c_str());

    auto it = txn.GetWriteSet().find(key);
    // Read your own writes, check the write set first.
    if (it != txn.GetWriteSet().end()) {
        value = it->second;
        return REPLY_OK;
    }

    Promise promise(GET_TIMEOUT);
    // Otherwise, do the GET
    client->Get(txnid, key, txn.GetTimestamp(), &promise);
    
    if (promise.GetReply() == REPLY_OK) {
        Debug("Adding [%s] with ts %lu to the read set", key.c_str(), promise.GetValue(key).GetTimestamp());
        txn.AddReadSet(key, promise.GetValue(key).GetInterval());
        if (((txn.IsolationMode() == READ_ONLY) || (txn.IsolationMode() == SNAPSHOT_ISOLATION)) &&
            !txn.HasTimestamp()) {
            txn.SetTimestamp(promise.GetValue(key).GetTimestamp());
            Debug("Setting ts to %lu", txn.GetTimestamp());
        }
    }

    value = promise.GetValues()[key].GetValue();

    return promise.GetReply();
}

int
DiamondClient::MultiGet(const vector<string> &keys, map<string, string> &values)
{
    if (txnid == 0) {
        Panic("Doing a GET outside a transaction. YOU ARE A BAD PERSON!!");
    }

    Debug("MULTIGET [%lu] %lu", txnid, keys.size());

    // create a list of keys to get
    vector<string> keysToRead;
    for (auto key : keys) {
        auto it = txn.GetWriteSet().find(key); 
        // Read your own writes, check the write set first.
        if (it == txn.GetWriteSet().end()) {
            keysToRead.push_back(key);
        } else {
            values[key] = it->second;
        }
    }

    if (keysToRead.size() == 0) {
        return REPLY_OK;
    }

    Promise promise(GET_TIMEOUT);
    client->MultiGet(txnid, keysToRead, txn.GetTimestamp(), &promise);
        
    if (promise.GetReply() == REPLY_OK){
        std::map<string, Version> values = promise.GetValues();
        for (auto &value : values) {
            Debug("Adding [%s] with ts %lu to the read set", value.first.c_str(), value.second.GetTimestamp());
            txn.AddReadSet(value.first, value.second.GetInterval());
            values[value.first] = value.second.GetValue();
        }

        if (((txn.IsolationMode() == READ_ONLY) || (txn.IsolationMode() == SNAPSHOT_ISOLATION)) &&
            !txn.HasTimestamp()) {
            txn.SetTimestamp((values.begin())->second.GetTimestamp());
            Debug("Setting ts to %lu", txn.GetTimestamp());
        }
    }
    
    return promise.GetReply();
}

/* Sets the value corresponding to the supplied key. */
int
DiamondClient::Put(const string &key, const string &value)
{
    if (txnid == 0) {
        Panic("Doing a PUT outside a transaction. YOU ARE A BAD PERSON!!");
    }

    if (txn.IsReadOnly()) {
        Panic("Can't do a put in a read only transaction!");
    }

    Debug("PUT [%lu] %s %s", txnid, key.c_str(), value.c_str());
    
    // Update the write set.
    txn.AddWriteSet(key, value);
    return REPLY_OK;
}

int
DiamondClient::Increment(const string &key, const int inc)
{
    if (txnid == 0) {
        Panic("Doing a PUT outside a transaction. YOU ARE A BAD PERSON!!");
    }

    if (txn.IsReadOnly()) {
        Panic("Can't do a put in a read only transaction!");
    }

    Debug("INCREMENT [%lu] %s %i", txnid, key.c_str(), inc);
    
    // Update the write set.
    txn.AddIncrementSet(key, inc);
    return REPLY_OK;
}

/* Attempts to commit the ongoing transaction. */
bool
DiamondClient::Commit()
{
    if (txnid == 0) {
        Panic("Doing a COMMIT outside a transaction. YOU ARE A BAD PERSON!!");
    }

    Debug("COMMIT [%lu]", txnid);
    
    Promise promise(COMMIT_TIMEOUT);

    client->Commit(txnid, txn, &promise);
    int status = promise.GetReply();
    txnid = 0;
    txn = Transaction();
    return status == REPLY_OK;
}

/* Aborts the ongoing transaction. */
void
DiamondClient::Abort()
{
    if (txnid == 0) {
        Panic("Doing an ABORT outside a transaction. YOU ARE A BAD PERSON!!");
    }

    Debug("ABORT [%lu]",txnid);

    Promise promise(COMMIT_TIMEOUT);
    
    client->Abort(txnid, &promise);
    // block until abort returns
    promise.GetReply();
    txnid = 0;
    txn = Transaction();
}

uint64_t DiamondClient::GetNextNotification()
{
    Promise p;
    client->GetNextNotification(&p);
    return p.GetReactiveId();
}

} // namespace diamond
