/* S4 tiny synthetic operators only. No loader, training, model or product executor. */
#include <float.h>
#include <inttypes.h>
#include <limits.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>

_Static_assert(FLT_RADIX == 2 && FLT_MANT_DIG == 24 && sizeof(float) == 4,
               "binary32 required");

static int quant(float x, float scale, int8_t *out)
{
    if (!isfinite(x) || !isfinite(scale) || scale <= 0.0f) return 0;
    /* Exact binary32 operands promoted to binary64. Saturate before int conversion. */
    const double z = (double)x / (double)scale;
    if (z >= 127.0) { *out = INT8_C(127); return 1; }
    if (z <= -127.0) { *out = -INT8_C(127); return 1; }
    const double lo = floor(z);
    int32_t v = (int32_t)lo;
    const double frac = z-lo;
    if (frac > 0.5 || (frac == 0.5 && v % 2 != 0)) ++v;
    *out = (int8_t)v;
    return 1;
}

static int add_product(int32_t acc, int8_t a, int8_t b, int32_t *out)
{
    const int64_t next = (int64_t)acc + (int64_t)a * (int64_t)b;
    if (next < INT32_MIN || next > INT32_MAX) return 0;
    *out = (int32_t)next;
    return 1;
}

static int dot_i8(const int8_t *a, const int8_t *b, size_t n, int32_t *out)
{
    int32_t acc = 0;
    for (size_t j=0; j<n; ++j) {
        if (!add_product(acc,a[j],b[j],&acc)) return 0;
    }
    *out = acc;
    return 1;
}

static float dot_f32(const float *a, const float *b, size_t n)
{
    float acc = 0.0f;
    for (size_t j=0; j<n; ++j) {
        const float product = a[j]*b[j];
        acc = acc+product;
    }
    return acc;
}

int main(void)
{
    const float xs[] = {0.0f,0.25f,0.75f,1.25f,1.75f,-0.25f,-0.75f,-1.25f,-1.75f,
        0.24999998509883880615234375f,0.2500000298023223876953125f,
        -0.24999998509883880615234375f,-0.2500000298023223876953125f,
        63.5f,63.75f,1000000.0f,-63.5f,-63.75f,-1000000.0f,
        0.125f,-0.125f,0.375f,-0.375f};
    const size_t nq = sizeof xs/sizeof xs[0];
    for (size_t i=0; i<nq; ++i) {
        int8_t q=0;
        const float scale = i>=19 ? 0.25f : 0.5f;
        if (!quant(xs[i],scale,&q)) return 1;
        printf("Q %zu %d\n",i,(int)q);
    }
    const float invalid_x[] = {NAN,INFINITY,-INFINITY,1.0f,1.0f,1.0f,1.0f};
    const float invalid_s[] = {1.0f,1.0f,1.0f,0.0f,-1.0f,NAN,INFINITY};
    for (size_t i=0; i<sizeof invalid_x/sizeof invalid_x[0]; ++i) {
        int8_t q=42;
        printf("R %zu %d\n",i,quant(invalid_x[i],invalid_s[i],&q));
    }
    int32_t result=0;
    printf("OVERFLOW_POS %d\n",add_product(INT32_MAX,1,1,&result));
    printf("OVERFLOW_NEG %d\n",add_product(INT32_MIN,-1,1,&result));
    if (!add_product(INT32_MAX-1,1,1,&result)) return 1;
    printf("EDGE_MAX %" PRId32 "\n",result);
    if (!add_product(INT32_MIN+1,-1,1,&result)) return 1;
    printf("EDGE_MIN %" PRId32 "\n",result);
    const float input[4]={0.5f,-1.25f,0.75f,0.25f};
    const float weights[4][4]={{0.25f,0.5f,-0.75f,1.0f},
        {1.25f,-0.25f,0.25f,-0.5f},
        {-1.0f,0.5f,0.5f,0.125f},
        {1.25f,-0.25f,0.25f,-0.5f}};
    const float scale[4]={0.25f,0.25f,0.125f,0.25f};
    int8_t qi[4]={0};
    for (size_t j=0;j<4;++j) if (!quant(input[j],0.25f,&qi[j])) return 1;
    for (size_t i=0;i<4;++i) {
        int8_t qw[4]={0};
        for (size_t j=0;j<4;++j) if (!quant(weights[i][j],scale[i],&qw[j])) return 1;
        if (!dot_i8(qw,qi,4,&result)) return 1;
        const float fp=dot_f32(weights[i],input,4);
        const float deq=(float)result*(scale[i]*0.25f);
        printf("ROW %zu %" PRId32 " %.9g %.9g\n",i,result,(double)fp,(double)deq);
    }
    /* Tie-breaking: first/lowest class ID on exact equal score. */
    const float ties[3][3]={{1.0f,1.0f,0.5f},
        {1.0f,1.00000011920928955078125f,1.0f},
        {-1.0f,-1.0f,-2.0f}};
    for (size_t j=0;j<3;++j) {
        size_t best=0;
        for (size_t i=1;i<3;++i) if (ties[j][i]>ties[j][best]) best=i;
        printf("TOP %zu %zu\n",j,best);
    }
    return fflush(stdout)==0 ? 0 : 1;
}
