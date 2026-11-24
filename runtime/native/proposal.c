#include "proposal.h"

#include <stddef.h>

enum dictum_proposal_status dictum_propose(const char *instruction)
{
    if (instruction == NULL || instruction[0] == '\0') {
        return DICTUM_PROPOSAL_INVALID_INPUT;
    }
    return DICTUM_PROPOSAL_UNSUPPORTED;
}
