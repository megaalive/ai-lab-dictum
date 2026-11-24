#include "b2_linear.h"
#include "ir_wire.h"
#include <string.h>

static bool word_byte(unsigned char c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || c >= 128u;
}

bool b2_extract(const unsigned char *input, size_t len,
                const struct b2_span *mask, size_t mask_count,
                struct b2_features *out)
{
    if (out == NULL) return false;
    memset(out, 0, sizeof(*out));
    if (input == NULL || ir_check_input(input, len) != IR_OK ||
        mask_count > B2_MASK_MAX || (mask_count != 0 && mask == NULL)) return false;
    for (size_t i = 0; i < mask_count; ++i) {
        if (!ir_check_span(input, len, mask[i].start, mask[i].end) ||
            (i != 0 && mask[i-1].end > mask[i].start)) return false;
    }
    bool seen[B2_DIM] = {false};
    size_t p = 0, m = 0;
    while (p < len) {
        if (!word_byte(input[p])) { ++p; continue; }
        size_t start = p;
        uint32_t hash = UINT32_C(2166136261);
        while (p < len && word_byte(input[p])) {
            unsigned char c = input[p++];
            if (c >= 'A' && c <= 'Z') c = (unsigned char)(c + ('a'-'A'));
            hash = (hash ^ (uint32_t)c) * UINT32_C(16777619);
        }
        while (m < mask_count && mask[m].end <= start) ++m;
        if (m < mask_count && mask[m].start < p) continue;
        seen[hash % B2_DIM] = true;
    }
    for (size_t i = 0; i < B2_DIM; ++i)
        if (seen[i]) out->ids[out->count++] = (uint16_t)i;
    return true;
}

bool b2_scores(const struct b2_weights *model, const struct b2_features *features,
               int64_t scores[B2_CLASSES])
{
    if (scores == NULL) return false;
    memset(scores, 0, sizeof(int64_t)*B2_CLASSES);
    if (model == NULL || features == NULL || features->count > B2_DIM) return false;
    for (size_t i = 0; i < features->count; ++i)
        if (features->ids[i] >= B2_DIM ||
            (i != 0 && features->ids[i-1] >= features->ids[i])) return false;
    for (size_t c = 0; c < B2_CLASSES; ++c) {
        int64_t score = model->bias[c];
        for (size_t i = 0; i < features->count; ++i)
            score += model->weights[c][features->ids[i]];
        scores[c] = score;
    }
    return true;
}

int b2_rank(const struct b2_features *features,
            const int64_t scores[B2_CLASSES], uint32_t min_margin)
{
    if (features == NULL || features->count == 0 || features->count > B2_DIM ||
        scores == NULL || min_margin == 0) return -1;
    /* Scores from the int16 model cannot exceed this bound. */
    const int64_t bound = INT64_C(32768) * (B2_DIM + 1u);
    for (size_t c = 0; c < B2_CLASSES; ++c)
        if (scores[c] < -bound || scores[c] > bound) return -1;
    size_t best = 0, second = 1;
    if (scores[second] > scores[best]) { best = 1; second = 0; }
    for (size_t c = 2; c < B2_CLASSES; ++c) {
        if (scores[c] > scores[best]) { second = best; best = c; }
        else if (scores[c] > scores[second]) second = c;
    }
    if (scores[best] - scores[second] < (int64_t)min_margin) return -1;
    return (int)best;
}
