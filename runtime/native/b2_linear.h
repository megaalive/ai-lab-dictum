#ifndef DICTUM_B2_LINEAR_H
#define DICTUM_B2_LINEAR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Development classifier mechanics only; not linked into dictum CLI. */
#define B2_CLASSES 48u
#define B2_DIM 1024u
#define B2_MASK_MAX 32u

struct b2_span { size_t start, end; };
struct b2_features { uint16_t ids[B2_DIM]; size_t count; };
struct b2_weights {
    int16_t weights[B2_CLASSES][B2_DIM];
    int16_t bias[B2_CLASSES];
};
bool b2_extract(const unsigned char *input, size_t len,
                const struct b2_span *mask, size_t mask_count,
                struct b2_features *out);
bool b2_scores(const struct b2_weights *model, const struct b2_features *features,
               int64_t scores[B2_CLASSES]);
/* Returns zero-based class, or -1 on tie, inadequate margin or empty features.
 * The margin is an uncalibrated integer, never authorization. */
int b2_rank(const struct b2_features *features,
            const int64_t scores[B2_CLASSES], uint32_t min_margin);
#endif
