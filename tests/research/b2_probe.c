/* Numeric development oracle, not a product model loader. */
#include "b2_linear.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    unsigned char frame[1u + 4u*B2_MASK_MAX + 4096u + 1u];
    struct b2_span masks[B2_MASK_MAX];
    struct b2_features features;
    static struct b2_weights model;
    int64_t scores[B2_CLASSES];
    if (argc != 2) return 2;
    bool tie = strcmp(argv[1], "tie") == 0;
    bool margin = strcmp(argv[1], "margin") == 0;
    if (!tie && !margin && strcmp(argv[1], "regular") != 0) return 2;
    size_t n = fread(frame, 1, sizeof(frame), stdin);
    if (ferror(stdin)) return 2;
    if (n == 0 || frame[0] > B2_MASK_MAX) { puts("reject"); return 0; }
    size_t count = frame[0], start = 1u + 4u*count;
    if (n <= start) { puts("reject"); return 0; }
    for (size_t i = 0; i < count; ++i) {
        size_t p = 1u + 4u*i;
        masks[i].start = (size_t)frame[p] | ((size_t)frame[p+1] << 8);
        masks[i].end = (size_t)frame[p+2] | ((size_t)frame[p+3] << 8);
    }
    if (!b2_extract(frame+start, n-start, masks, count, &features)) {
        puts("reject"); return 0;
    }
    if (!tie) {
        for (size_t c = 0; c < B2_CLASSES; ++c) {
            model.bias[c] = (int16_t)((int)(c % 11u)-5);
            for (size_t i = 0; i < B2_DIM; ++i)
                model.weights[c][i] = (int16_t)((int)(((c+3u)*(i+7u)+i/17u) % 23u)-11);
        }
    }
    if (!b2_scores(&model, &features, scores)) return 3;
    printf("%d\n", b2_rank(&features, scores, margin ? 1000u : 1u));
    for (size_t i = 0; i < features.count; ++i) printf("%u ", (unsigned)features.ids[i]);
    putchar('\n');
    for (size_t c = 0; c < B2_CLASSES; ++c) printf("%" PRId64 " ", scores[c]);
    putchar('\n');
    return 0;
}
