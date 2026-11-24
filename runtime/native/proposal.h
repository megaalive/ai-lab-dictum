#ifndef DICTUM_PROPOSAL_H
#define DICTUM_PROPOSAL_H

enum dictum_proposal_status {
    DICTUM_PROPOSAL_INVALID_INPUT,
    DICTUM_PROPOSAL_UNSUPPORTED
};

/* Pinjam string selama panggilan. Input null atau kosong dianggap tidak valid. */
enum dictum_proposal_status dictum_propose(const char *instruction);

#endif
