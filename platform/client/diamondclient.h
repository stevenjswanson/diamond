// -*- mode: c++; c-file-style: "k&r"; c-basic-offset: 4 -*-
// vim: set ts=4 sw=4:
/***********************************************************************
 *
 * client/diamondclient.h:
 *   Diamond transactional store interface
 *
 * Copyright 2015 Irene Zhang  <iyzhang@cs.washington.edu>
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
 
#ifndef _DIAMOND_CLIENT_H_
#define _DIAMOND_CLIENT_H_

#include "lib/assert.h"
#include "lib/message.h"
#include "lib/configuration.h"
#include "lib/tcptransport.h"
#include "frontend/client.h"
#include "store/common/frontend/client.h"
#include "store/common/frontend/cacheclient.h"
#include "store/common/frontend/bufferclient.h"

#include <condition_variable>
#include <mutex>
#include <string>
#include <set>
#include <thread>
#include <vector>

namespace diamond {

class DiamondClient : public Client
{
public:
    DiamondClient(std::string configPath);
    ~DiamondClient();

    // Overriding functions from ::Client
    void Begin();
    int Get(const std::string &key, std::string &value);
    int MultiGet(const std::vector<std::string> &keys, std::map<std::string, std::string> &value);
    int Put(const std::string &key, const std::string &value);
    bool Commit();
    void Abort();

private:    
    /* Private helper functions. */
    void run_client(); // Runs the transport event loop.

    // Unique ID for this client.
    uint64_t client_id;

    // transaction id counter
    uint64_t txnid_counter;
    // its lock
    std::mutex txnid_lock;
    
    // Ongoing transaction ID.
    std::map<std::thread::id, uint64_t> ongoing;

    // Transport used by storage client proxies.
    TCPTransport transport;
    
    // Thread running the transport event loop.
    std::thread *clientTransport;

    // Caching client for the store
    BufferClient *bclient;
};

} // namespace diamond

#endif /* _DIAMOND_CLIENT_H_ */