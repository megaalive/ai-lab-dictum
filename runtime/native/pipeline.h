#ifndef DICTUM_PIPELINE_H
#define DICTUM_PIPELINE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum pipeline_model { PIPE_B0, PIPE_B1 };
enum pipeline_outcome { PIPE_PROPOSAL, PIPE_CLARIFY, PIPE_UNSUPPORTED, PIPE_DENY, PIPE_INTERNAL };
#define PIPE_FRAME 8192u

/* Owns all results; no raw instruction or external authority is retained.
 * Stages are for synthetic test inspection only. CLI publishes view only.
 * One synchronous request, no persisted/cross-process context or execution. */
struct pipeline_result {
    enum pipeline_outcome outcome;
    char context[2048];
    char nlu[PIPE_FRAME], ir[PIPE_FRAME], policy[PIPE_FRAME], plan[PIPE_FRAME];
    char view[PIPE_FRAME];
};

bool pipeline_run(const unsigned char *input, size_t size, int64_t reference_unix_s,
                  uint64_t request_sequence, enum pipeline_model model,
                  struct pipeline_result *out);
bool pipeline_search(const char *id, char out[PIPE_FRAME]);
bool pipeline_inspect(char out[PIPE_FRAME]);

#endif
