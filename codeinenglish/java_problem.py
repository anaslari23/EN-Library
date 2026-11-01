"""Java backend for problem requests (recipes and core algorithm families)."""

from __future__ import annotations

import json
from .errors import CodeInEnglishError
from .problem_recognizer import ProblemFamily, ProblemSpec
from .recipes import BY_KEY


def generate_java_problem(spec: ProblemSpec, filename: str) -> str:
    """Generate self-contained Java source for a ProblemSpec."""
    family = spec.family
    key = family.value if hasattr(family, "value") else str(family)

    func_code = _get_java_implementation(spec, filename)
    name = spec.function_name
    examples_code = _generate_java_examples(spec)

    return f'''import java.io.*;
import java.util.*;

public class Solution {{
{func_code}

    public static void main(String[] args) {{
        List<String> argList = Arrays.asList(args);
        if (argList.contains("--check-examples")) {{
{examples_code}
        }}
    }}
}}
'''


def _get_java_implementation(spec: ProblemSpec, filename: str) -> str:
    family = spec.family
    key = family.value if hasattr(family, "value") else str(family)

    if key == "two_sum":
        return '''    public static List<Long> two_sum(List<Long> nums, long target) {
        Map<Long, Long> seen = new HashMap<>();
        for (int i = 0; i < nums.size(); i++) {
            long complement = target - nums.get(i);
            if (seen.containsKey(complement)) {
                return Arrays.asList(seen.get(complement), (long) i);
            }
            seen.put(nums.get(i), (long) i);
        }
        return null;
    }'''

    if key == "binary_search":
        return '''    public static long binary_search(List<Long> nums, long target) {
        int low = 0, high = nums.size() - 1;
        while (low <= high) {
            int mid = low + (high - low) / 2;
            if (nums.get(mid) == target) return (long) mid;
            if (nums.get(mid) < target) low = mid + 1;
            else high = mid - 1;
        }
        return -1L;
    }'''

    if key in ("duplicates", "contains_duplicate"):
        return '''    public static boolean contains_duplicate(List<Long> nums) {
        Set<Long> seen = new HashSet<>();
        for (long n : nums) {
            if (!seen.add(n)) return true;
        }
        return false;
    }'''

    if key in ("minimum", "find_minimum"):
        return '''    public static Long find_minimum(List<Long> nums) {
        if (nums == null || nums.isEmpty()) return null;
        return Collections.min(nums);
    }'''

    if key in ("maximum", "find_maximum"):
        return '''    public static Long find_maximum(List<Long> nums) {
        if (nums == null || nums.isEmpty()) return null;
        return Collections.max(nums);
    }'''

    if key in ("sum", "calculate_sum"):
        return '''    public static long calculate_sum(List<Long> nums) {
        long total = 0;
        if (nums != null) {
            for (long n : nums) total += n;
        }
        return total;
    }'''

    if key in ("reverse_text",):
        return '''    public static String reverse_text(String text) {
        if (text == null) return null;
        return new StringBuilder(text).reverse().toString();
    }'''

    if key in ("palindrome", "is_palindrome"):
        return '''    public static boolean is_palindrome(String text) {
        if (text == null) return false;
        StringBuilder cleaned = new StringBuilder();
        for (char c : text.toCharArray()) {
            if (Character.isLetterOrDigit(c)) {
                cleaned.append(Character.toLowerCase(c));
            }
        }
        String s = cleaned.toString();
        return s.equals(new StringBuilder(s).reverse().toString());
    }'''

    if key in ("sort_ascending",):
        return '''    public static List<Long> sort_ascending(List<Long> nums) {
        if (nums == null) return new ArrayList<>();
        List<Long> result = new ArrayList<>(nums);
        Collections.sort(result);
        return result;
    }'''

    if key in ("move_zeros",):
        return '''    public static List<Long> move_zeros(List<Long> nums) {
        if (nums == null) return new ArrayList<>();
        List<Long> result = new ArrayList<>();
        int zeros = 0;
        for (long n : nums) {
            if (n == 0) zeros++;
            else result.add(n);
        }
        for (int i = 0; i < zeros; i++) result.add(0L);
        return result;
    }'''

    if key in ("merge_sorted_lists",):
        return '''    public static List<Long> merge_sorted_lists(List<Long> first, List<Long> second) {
        List<Long> result = new ArrayList<>();
        int i = 0, j = 0;
        while (i < first.size() && j < second.size()) {
            if (first.get(i) <= second.get(j)) result.add(first.get(i++));
            else result.add(second.get(j++));
        }
        while (i < first.size()) result.add(first.get(i++));
        while (j < second.size()) result.add(second.get(j++));
        return result;
    }'''

    if key in ("maximum_subarray_sum",):
        return '''    public static Long maximum_subarray_sum(List<Long> nums) {
        if (nums == null || nums.isEmpty()) return null;
        long current = nums.get(0), best = nums.get(0);
        for (int i = 1; i < nums.size(); i++) {
            current = Math.max(nums.get(i), current + nums.get(i));
            best = Math.max(best, current);
        }
        return best;
    }'''

    if key in ("balanced_delimiters", "has_balanced_delimiters"):
        return '''    public static boolean has_balanced_delimiters(String text) {
        if (text == null) return true;
        Deque<Character> stack = new ArrayDeque<>();
        for (char c : text.toCharArray()) {
            if (c == '(' || c == '[' || c == '{') stack.push(c);
            else if (c == ')' || c == ']' || c == '}') {
                if (stack.isEmpty()) return false;
                char open = stack.pop();
                if (c == ')' && open != '(') return false;
                if (c == ']' && open != '[') return false;
                if (c == '}' && open != '{') return false;
            }
        }
        return stack.isEmpty();
    }'''

    if key in ("frequencies", "count_frequencies"):
        return '''    public static Map<Long, Long> count_frequencies(List<Long> nums) {
        Map<Long, Long> counts = new HashMap<>();
        if (nums != null) {
            for (long n : nums) counts.put(n, counts.getOrDefault(n, 0L) + 1L);
        }
        return counts;
    }'''

    if key in ("first_unique_character",):
        return '''    public static String first_unique_character(String text) {
        if (text == null) return null;
        Map<Character, Integer> counts = new LinkedHashMap<>();
        for (char c : text.toCharArray()) counts.put(c, counts.getOrDefault(c, 0) + 1);
        for (Map.Entry<Character, Integer> e : counts.entrySet()) {
            if (e.getValue() == 1) return String.valueOf(e.getKey());
        }
        return null;
    }'''

    if key in ("anagram", "are_anagrams"):
        return '''    public static boolean are_anagrams(String first, String second) {
        if (first == null || second == null) return false;
        char[] a = first.toCharArray(), b = second.toCharArray();
        Arrays.sort(a);
        Arrays.sort(b);
        return Arrays.equals(a, b);
    }'''

    # Recipes
    if key == "factorial":
        return '''    public static Long factorial(long n) {
        if (n < 0) return null;
        long result = 1;
        for (long v = 2; v <= n; v++) result *= v;
        return result;
    }'''

    if key == "fibonacci":
        return '''    public static Long fibonacci(long n) {
        if (n < 0) return null;
        long prev = 0, curr = 1;
        for (int i = 0; i < n; i++) {
            long next = prev + curr;
            prev = curr;
            curr = next;
        }
        return prev;
    }'''

    if key == "is_prime":
        return '''    public static boolean is_prime(long n) {
        if (n < 2) return false;
        for (long d = 2; d * d <= n; d++) {
            if (n % d == 0) return false;
        }
        return true;
    }'''

    if key == "gcd":
        return '''    public static long greatest_common_divisor(long first, long second) {
        first = Math.abs(first);
        second = Math.abs(second);
        while (second != 0) {
            long temp = second;
            second = first % second;
            first = temp;
        }
        return first;
    }'''

    if key == "is_even":
        return '''    public static boolean is_even(long n) {
        return n % 2 == 0;
    }'''

    if key == "count_vowels":
        return '''    public static long count_vowels(String text) {
        if (text == null) return 0L;
        long count = 0;
        for (char c : text.toLowerCase().toCharArray()) {
            if ("aeiou".indexOf(c) >= 0) count++;
        }
        return count;
    }'''

    raise CodeInEnglishError(filename, 1, f"Java output does not yet support {key} problems", kind="unsupported")


def _to_java_literal(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value}L"
    if isinstance(value, float):
        return f"{value}"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        items = ", ".join(_to_java_literal(v) for v in value)
        return f"Arrays.asList({items})"
    if isinstance(value, dict):
        entries = []
        for k, v in value.items():
            k_code = _to_java_literal(k)
            v_code = _to_java_literal(v)
            entries.append(f"map.put({k_code}, {v_code});")
        return f"Collections.unmodifiableMap(new HashMap<>() {{{{ {' '.join(entries)} }}}})"
    return str(value)


def _generate_java_examples(spec: ProblemSpec) -> str:
    lines = []
    lines.append(f'            int totalExamples = {len(spec.examples)};')
    lines.append(f'            int passed = 0;')
    name = spec.function_name

    for i, ex in enumerate(spec.examples, 1):
        args_code = []
        for inp in spec.inputs:
            val = ex.input.get(inp.name)
            args_code.append(_to_java_literal(val))
        call = f"{name}({', '.join(args_code)})"
        expected = _to_java_literal(ex.expected)
        lines.append(f'            Object actual{i} = {call};')
        lines.append(f'            Object expected{i} = {expected};')
        lines.append(f'            if (!Objects.deepEquals(actual{i}, expected{i})) {{')
        lines.append(f'                System.err.println("Example {i} failed: got " + actual{i} + " expected " + expected{i});')
        lines.append(f'                System.exit(1);')
        lines.append(f'            }}')
        lines.append(f'            passed++;')

    lines.append(f'            System.out.println("All " + passed + " examples passed.");')
    return "\n".join(lines)
