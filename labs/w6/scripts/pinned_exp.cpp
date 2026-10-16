// w6 Part A: exports the CIS-2 pinned exponential (from the PATCHED engine
// source, default build, no substitution macro) to the C harness.
#include "cis2_fpenv.h"
#include "cis2_math.h"
extern "C" float w6_pinned_exp(float x) { return cis2_exp_pinned(x); }
