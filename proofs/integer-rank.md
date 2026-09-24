# Exact positive count-word barrier theorem

## 1. Bilinear bag-count fragment

Let `A in N^(m x n)` and let

    f_A(x,y) = sum_{i=1}^m sum_{j=1}^n A_ij x_i y_j.

The variables are multiplicities of finitely many left and right input tags.  A
finite tuple of output tags is handled by concatenating the corresponding
coefficient matrices; the scalar presentation keeps notation small.

The source syntax uses natural constants, addition, and multiplication.  An
admission judgment accepts only zero-preserving expressions whose normal form
is bilinear across the left/right partition.  This judgment is semantic for the
theorem; the artifact contains two bounded executable realizations, one based
on a complete probe family for its finite AST and one based on a separately
implemented monomial quotient.

## 2. Positive word machine

The prefix may read x but not y.  The continuation may read y but not x.  At the
barrier at most M natural-number words persist in fast state.  Any additional
natural word that crosses the barrier must be written once to slow storage and
read once later, at one transfer per operation.  Two transient arithmetic
buffers are available within a phase and are cleared at the barrier.

Control and addresses are static.  Arithmetic consists of natural constants,
addition, and multiplication.  There is no subtraction, division, comparison,
branching on a packed value, bit extraction, or uncharged variable-address
channel.  Output is append-only and unreadable.  Prefix summaries may be
arbitrary zero-preserving positive polynomials, not merely linear forms.

## 3. Rank measure

The nonnegative integer rank of A is

    rho_N(A) = min { r | A = U V, U in N^(m x r), V in N^(r x n) }.

Equivalently, it is the smallest number of nonzero rank-one natural matrices
whose sum is A.  The measure predates this work; the contribution here is its
exact operational role under the declared positive barrier and its use in a
proof-producing bag compiler.

## 4. Positive substitution lemma

### Lemma I1

Suppose a correct positive-word implementation carries k dynamic words
`S_1(x),...,S_k(x)` across the barrier and computes

    H(S_1(x),...,S_k(x),y) = f_A(x,y)

as a polynomial identity over N.  Then `rho_N(A) <= k`.

### Proof

Each S_l is a zero-preserving polynomial in x with nonnegative integer
coefficients, and H is a polynomial in summary indeterminates z and y with
nonnegative integer coefficients.  Because the target has degree exactly one
in x and one in y, positivity forbids cancellation of any substituted monomial
of higher x-degree, higher y-degree, or a wrong partition degree.

For each l let `u_il` be the coefficient of x_i in S_l.  Let `v_lj` be the
coefficient of `z_l y_j` in H.  A target monomial x_i y_j can arise only by
choosing the linear x_i term of one summary S_l and the z_l y_j term of H.
Zero-preservation rules out contributions through powers of a summary with a
constant term.  All other choices have the wrong degree and, because their
coefficients are nonnegative, would remain visible rather than cancel.
Therefore

    A_ij = sum_l u_il v_lj.

Writing U=(u_il) and V=(v_lj) gives a nonnegative integer factorization with k
columns/rows.

This argument is why a nonlinear positive summary cannot secretly carry two
independent linear channels in one count word.  It would cease to be valid in a
machine with subtraction, bit packing and extraction, or input-dependent
control; those are different capability signatures.

## 5. Lower bound

If s slow words cross the barrier, at most M+s dynamic summary words are
available to the continuation.  Lemma I1 gives

    rho_N(A) <= M+s,

so `s >= max(0,rho_N(A)-M)`.  Every slow summary is written and read once after
normalization, hence every correct implementation incurs at least

    2 * max(0,rho_N(A)-M)

word transfers.

## 6. Matching factor compiler

Given `A=UV` of width r, the prefix computes

    s_l = sum_i U_il x_i

for l=1,...,r.  It retains any min(M,r) summaries in fast words and writes the
rest once.  The continuation reloads each spilled summary once and emits

    sum_l s_l (sum_j V_lj y_j).

Distributivity gives exactly f_A.  The transfer cost is
`2*max(0,r-M)`; using a minimum-width factorization gives the lower bound.

### Theorem I2 (exact positive-word cost)

For the declared positive count-word barrier,

    OPT_pos(A,M) = 2 * max(0, rho_N(A)-M).

The theorem is a temporary-word-transfer result.  It does not count base reads,
output traffic, static code, coefficient storage, or physical bytes, and it is
not a theorem for arbitrary RAM programs.

## 7. Exact tiny certificates

For each bounded target A, the synthesizer enumerates every nonzero natural
rank-one atom R <= A and solves a shortest-path dynamic program over all
entrywise residual matrices.  A packet contains (1) a factor witness and (2) a
Bellman potential giving the optimal remaining atom count at every residual.
The independent checker regenerates atoms in another order, checks the factor
sum, and checks every feasible transition inequality together with equality
along the witness.  Unit atoms guarantee reachability.

The retained 64 instances include all binary two-by-two matrices, selected
nonbinary two-by-two and binary three-by-three cases, and identity matrices of
orders one through six.  They generate 7,378 checked Bellman inequalities and
10,743 numeric comparisons of extracted schedules with direct bilinear
evaluation.  A separate natural-polynomial normalizer checks all 64 symbolic
factor identities.  These bounded certificates support the implementation and
examples; the general lower bound is Lemma I1.
