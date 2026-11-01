"""C backend for problem requests (recipes and core numeric/text algorithm families)."""

from __future__ import annotations

import json
from .errors import CodeInEnglishError
from .problem_recognizer import ProblemFamily, ProblemSpec


def generate_c_problem(spec: ProblemSpec, filename: str) -> str:
    """Generate self-contained C99 source for a ProblemSpec."""
    family = spec.family
    key = family.value if hasattr(family, "value") else str(family)

    func_code = _get_c_implementation(spec, filename)
    examples_code = _generate_c_examples(spec)

    return f'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <ctype.h>

{func_code}

int main(int argc, char **argv) {{
    if (argc > 1 && strcmp(argv[1], "--check-examples") == 0) {{
{examples_code}
        return 0;
    }}
    return 0;
}}
'''


def _get_c_implementation(spec: ProblemSpec, filename: str) -> str:
    family = spec.family
    key = family.value if hasattr(family, "value") else str(family)

    if key == "binary_search":
        return '''long long binary_search(const long long *nums, int size, long long target) {
    int low = 0, high = size - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (nums[mid] == target) return (long long) mid;
        if (nums[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1LL;
}'''

    if key in ("minimum", "find_minimum"):
        return '''long long find_minimum(const long long *nums, int size) {
    if (size <= 0) return 0;
    long long m = nums[0];
    for (int i = 1; i < size; i++) {
        if (nums[i] < m) m = nums[i];
    }
    return m;
}'''

    if key in ("maximum", "find_maximum"):
        return '''long long find_maximum(const long long *nums, int size) {
    if (size <= 0) return 0;
    long long m = nums[0];
    for (int i = 1; i < size; i++) {
        if (nums[i] > m) m = nums[i];
    }
    return m;
}'''

    if key in ("sum", "calculate_sum"):
        return '''long long calculate_sum(const long long *nums, int size) {
    long long total = 0;
    for (int i = 0; i < size; i++) total += nums[i];
    return total;
}'''

    if key in ("duplicates", "contains_duplicate"):
        return '''bool contains_duplicate(const long long *nums, int size) {
    for (int i = 0; i < size; i++) {
        for (int j = i + 1; j < size; j++) {
            if (nums[i] == nums[j]) return true;
        }
    }
    return false;
}'''

    if key in ("reverse_text",):
        return '''char *reverse_text(const char *text) {
    if (!text) return NULL;
    int len = strlen(text);
    char *res = (char *) malloc(len + 1);
    for (int i = 0; i < len; i++) {
        res[i] = text[len - 1 - i];
    }
    res[len] = '\\0';
    return res;
}'''

    if key in ("palindrome", "is_palindrome"):
        return '''bool is_palindrome(const char *text) {
    if (!text) return false;
    int i = 0, j = strlen(text) - 1;
    while (i < j) {
        while (i < j && !isalnum((unsigned char) text[i])) i++;
        while (i < j && !isalnum((unsigned char) text[j])) j--;
        if (tolower((unsigned char) text[i]) != tolower((unsigned char) text[j])) return false;
        i++;
        j--;
    }
    return true;
}'''

    if key in ("maximum_subarray_sum",):
        return '''long long maximum_subarray_sum(const long long *nums, int size) {
    if (size <= 0) return 0;
    long long current = nums[0], best = nums[0];
    for (int i = 1; i < size; i++) {
        current = (nums[i] > current + nums[i]) ? nums[i] : current + nums[i];
        if (current > best) best = current;
    }
    return best;
}'''

    if key == "two_sum":
        return '''typedef struct { long long first; long long second; } Pair;
Pair two_sum(const long long *nums, int size, long long target) {
    Pair p = {-1, -1};
    for (int i = 0; i < size; i++) {
        for (int j = i + 1; j < size; j++) {
            if (nums[i] + nums[j] == target) {
                p.first = i;
                p.second = j;
                return p;
            }
        }
    }
    return p;
}'''

    # Recipes
    if key == "factorial":
        return '''long long factorial(long long n) {
    if (n < 0) return -1;
    long long res = 1;
    for (long long v = 2; v <= n; v++) res *= v;
    return res;
}'''

    if key == "fibonacci":
        return '''long long fibonacci(long long n) {
    if (n < 0) return -1;
    long long a = 0, b = 1;
    for (long long i = 0; i < n; i++) {
        long long next = a + b;
        a = b;
        b = next;
    }
    return a;
}'''

    if key == "is_prime":
        return '''bool is_prime(long long n) {
    if (n < 2) return false;
    for (long long d = 2; d * d <= n; d++) {
        if (n % d == 0) return false;
    }
    return true;
}'''

    if key == "gcd":
        return '''long long greatest_common_divisor(long long first, long long second) {
    if (first < 0) first = -first;
    if (second < 0) second = -second;
    while (second != 0) {
        long long temp = second;
        second = first % second;
        first = temp;
    }
    return first;
}'''

    if key == "is_even":
        return '''bool is_even(long long n) {
    return (n % 2 == 0);
}'''

    raise CodeInEnglishError(filename, 1, f"C output does not yet support {key} problems", kind="unsupported")


def _generate_c_examples(spec: ProblemSpec) -> str:
    lines = []
    lines.append('        int passed = 0;')
    name = spec.function_name
    key = spec.family.value if hasattr(spec.family, "value") else str(spec.family)

    for i, ex in enumerate(spec.examples, 1):
        lines.append(f'        // Example {i}')
        if key == "binary_search":
            nums = ex.input["nums"]
            target = ex.input["target"]
            expected = ex.expected
            nums_str = ", ".join(f"{x}LL" for x in nums)
            lines.append(f'        long long arr{i}[] = {{{nums_str}}};')
            lines.append(f'        long long act{i} = binary_search(arr{i}, {len(nums)}, {target}LL);')
            lines.append(f'        if (act{i} != {expected}LL) {{ fprintf(stderr, "Example {i} failed: got %lld expected %lld\\n", act{i}, {expected}LL); exit(1); }}')
            lines.append('        passed++;')
        elif key in ("minimum", "find_minimum", "maximum", "find_maximum", "sum", "calculate_sum", "maximum_subarray_sum"):
            nums = ex.input["nums"]
            expected = ex.expected
            nums_str = ", ".join(f"{x}LL" for x in nums)
            lines.append(f'        long long arr{i}[] = {{{nums_str}}};')
            lines.append(f'        long long act{i} = {name}(arr{i}, {len(nums)});')
            lines.append(f'        if (act{i} != {expected}LL) {{ fprintf(stderr, "Example {i} failed: got %lld expected %lld\\n", act{i}, {expected}LL); exit(1); }}')
            lines.append('        passed++;')
        elif key in ("duplicates", "contains_duplicate"):
            nums = ex.input["nums"]
            expected = "true" if ex.expected else "false"
            nums_str = ", ".join(f"{x}LL" for x in nums)
            lines.append(f'        long long arr{i}[] = {{{nums_str}}};')
            lines.append(f'        bool act{i} = contains_duplicate(arr{i}, {len(nums)});')
            lines.append(f'        if (act{i} != {expected}) {{ fprintf(stderr, "Example {i} failed\\n"); exit(1); }}')
            lines.append('        passed++;')
        elif key in ("reverse_text",):
            text = json.dumps(ex.input["text"])
            exp = json.dumps(ex.expected)
            lines.append(f'        char *act{i} = reverse_text({text});')
            lines.append(f'        if (strcmp(act{i}, {exp}) != 0) {{ fprintf(stderr, "Example {i} failed\\n"); exit(1); }}')
            lines.append(f'        free(act{i});')
            lines.append('        passed++;')
        elif key in ("palindrome", "is_palindrome"):
            text = json.dumps(ex.input["text"])
            expected = "true" if ex.expected else "false"
            lines.append(f'        bool act{i} = is_palindrome({text});')
            lines.append(f'        if (act{i} != {expected}) {{ fprintf(stderr, "Example {i} failed\\n"); exit(1); }}')
            lines.append('        passed++;')
        elif key == "two_sum":
            nums = ex.input["nums"]
            target = ex.input["target"]
            exp = ex.expected
            nums_str = ", ".join(f"{x}LL" for x in nums)
            lines.append(f'        long long arr{i}[] = {{{nums_str}}};')
            lines.append(f'        Pair act{i} = two_sum(arr{i}, {len(nums)}, {target}LL);')
            lines.append(f'        if (act{i}.first != {exp[0]}LL || act{i}.second != {exp[1]}LL) {{ fprintf(stderr, "Example {i} failed\\n"); exit(1); }}')
            lines.append('        passed++;')
        elif key in ("factorial", "fibonacci", "is_prime", "is_even"):
            val = ex.input.get("n", 0)
            exp = ex.expected
            if isinstance(exp, bool):
                exp_str = "true" if exp else "false"
                lines.append(f'        bool act{i} = {name}({val}LL);')
                lines.append(f'        if (act{i} != {exp_str}) {{ fprintf(stderr, "Example {i} failed\\n"); exit(1); }}')
            else:
                lines.append(f'        long long act{i} = {name}({val}LL);')
                lines.append(f'        if (act{i} != {exp}LL) {{ fprintf(stderr, "Example {i} failed\\n"); exit(1); }}')
            lines.append('        passed++;')

    lines.append('        printf("All %d examples passed.\\n", passed);')
    return "\n".join(lines)
