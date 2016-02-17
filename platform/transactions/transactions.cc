#include "includes/transactions.h"

#include <signal.h>
#include "lib/message.h"

namespace diamond {
    void TxnManager::Start() {
        evthread_use_pthreads();
        txnEventBase = event_base_new();
        evthread_make_base_notifiable(txnEventBase);

        event * sigtermEvent = evsignal_new(txnEventBase, SIGTERM, signalCallback, this);
        event * sigintEvent = evsignal_new(txnEventBase, SIGINT, signalCallback, this);

        evsignal_add(sigtermEvent, NULL);
        evsignal_add(sigintEvent, NULL);

        txnThread = new std::thread(&TxnManager::startHelper, this);
        reactiveThread = new std::thread(&TxnManager::reactiveLoop, this);
    }

    void TxnManager::reactiveLoop() {
        while(true) {
            sleep(1);
            for (auto it = reactiveList.begin(); it != reactiveList.end(); it++) {
                txn_function_t func = *it;
                DObject::TransactionBegin();
                func();
                DObject::TransactionCommit();
            }
        }
    }

    void TxnManager::startHelper() {
        event_base_dispatch(txnEventBase);
    }

    void TxnManager::signalCallback(evutil_socket_t fd, short what, void * arg) {
        Debug("Transaction manager terminating on SIGTERM/SIGINT");
        TxnManager * txnManager = (TxnManager *)arg;
        event_base_loopbreak(txnManager->txnEventBase);
    }

    int TxnManager::ExecuteTxn(txn_function_t func, txn_callback_t callback) {
        txn_info_t * info = new txn_info_t();
        info->func = func;
        info->callback = callback;
        event * ev = event_new(txnEventBase, -1, 0, executeTxnCallback, info);
        event_add(ev, NULL);
        event_active(ev, 0, 1);
        return 0;
    }

    void TxnManager::executeTxnCallback(evutil_socket_t fd, short what, void * arg) {
        txn_info_t * info = (txn_info_t *)arg;
        DObject::TransactionBegin();
        info->func();
        int committed = DObject::TransactionCommit();
        info->callback(committed);
        delete info;
    }

    //TODO: figure out and use interface for actual reactive txns instead of polling
    txn_id TxnManager::ReactiveTxn(txn_function_t func) {
        reactiveList.push_back(func);
        return 0;
    }

    void StartTxnManager() {
        if (txnManager == NULL) {
            txnManager = new TxnManager();
        }
        txnManager->Start();
    }

    int execute_txn(txn_function_t func) {
        int ret = execute_txn(func, [] (int committed) {});
        return ret;
    }

    int execute_txn(txn_function_t func, txn_callback_t callback) {
        if (txnManager == NULL) {
            Panic("txnManager is null"); 
        }
        int ret = txnManager->ExecuteTxn(func, callback);
        return ret;
    }

    txn_id reactive_txn(txn_function_t func) {
        if (txnManager == NULL) {
            Panic("txnManager is null"); 
        }
        txn_id id = txnManager->ReactiveTxn(func);
        return id;
    }

    void reactive_stop(txn_id id) {
        //TODO: implement
    }
    void abort_txn() {
        //TODO: implement
    }
}
