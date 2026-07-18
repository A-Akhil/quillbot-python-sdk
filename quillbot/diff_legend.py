import re

def mark_different(original_sentence: str, paraphrased_words: list) -> list:
    """
    Identifies 'Changed Words'.

    JS Original Code:
    g(v, "markDifferent", (e, t) => {
        let a = e.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
        return t.forEach(e => {
            let t = e.word;
            t = (t = t.replace("'s", "")).replace(/[^a-zA-Z0-9]/g, "").toLowerCase(), e.different = !a.includes(t)
        }), t
    })
    """
    orig_stripped = re.sub(r'[^a-zA-Z0-9]', '', original_sentence).lower()
    
    for word_obj in paraphrased_words:
        word = word_obj.get("word", "")
        # Remove 's and non-alphanumeric chars
        word_stripped = re.sub(r'[^a-zA-Z0-9]', '', word.replace("'s", "")).lower()
        word_obj["is_changed_word"] = word_stripped not in orig_stripped if word_stripped else False

    return paraphrased_words

def longest_common_substring(s1: str, s2: str) -> str:
    """
    Standard Longest Common Substring (LCS) algorithm using dynamic programming.
    
    JS Original Code:
    g(v, "longestCommonSubstring", (e, t) => {
        let a, s, n, i = [], r = 0, o = -1;
        for (a = 0; a < e.length; a += 1)
            for (s = 0, i[a] = []; s < t.length; s += 1) e.charAt(a) === t.charAt(s) ? a > 0 && s > 0 ? i[a][s] = i[a - 1][s - 1] + 1 : i[a][s] = 1 : i[a][s] = 0, i[a][s] > r && (r = i[a][s], o = a);
        return r > 0 ? (n = o - r + 1, e.substr(n, r)) : ""
    })
    """
    m, n = len(s1), len(s2)
    # Using a 1D array to optimize space instead of 2D
    dp = [0] * (n + 1)
    max_len = 0
    end_index = -1
    
    for i in range(1, m + 1):
        prev = 0
        for j in range(1, n + 1):
            temp = dp[j]
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev + 1
                if dp[j] > max_len:
                    max_len = dp[j]
                    end_index = i - 1
            else:
                dp[j] = 0
            prev = temp
            
    if max_len > 0:
        start_index = end_index - max_len + 1
        return s1[start_index:end_index + 1]
    return ""

def mark_longest_substring(original_sentence: str, paraphrased_words: list) -> list:
    """
    Identifies 'Longest Unchanged Words'.

    JS Original Code:
    g(v, "markLongestSubString", (e, t) => {
        e = e.toLowerCase();
        let a = t.map(e => e.word.toLowerCase()).join(" "),
            s = a.slice(), n = e.slice(), i = "";
        ...
        i = v.longestCommonSubstring(e, a).trim();
        ...
        let _ = 0;
        t.forEach(e => {
            let t = e.word.length, a = _, s = _ + t;
            (_ += t) >= r && _ - t <= o && (e.inLongestSubstr = !0, r > a && (e.inLongestSubstr = !1), o < s && (e.inLongestSubstr = !1)), _ += 1
        });
        ...
    """
    orig_lower = original_sentence.lower()
    para_string = " ".join([w.get("word", "").lower() for w in paraphrased_words])
    
    lcs = longest_common_substring(orig_lower, para_string).strip()
    
    # Initialize flag
    for w in paraphrased_words:
        w["in_longest_substring"] = False
        
    if not lcs:
        return paraphrased_words
        
    start_idx = para_string.find(lcs)
    end_idx = start_idx + len(lcs)
    
    if start_idx == -1:
        return paraphrased_words
        
    char_count = 0
    for word_obj in paraphrased_words:
        word_len = len(word_obj.get("word", ""))
        word_start = char_count
        word_end = char_count + word_len
        
        char_count += word_len
        
        if char_count >= start_idx and (char_count - word_len) <= end_idx:
            word_obj["in_longest_substring"] = True
            if start_idx > word_start:
                word_obj["in_longest_substring"] = False
            if end_idx < word_end:
                word_obj["in_longest_substring"] = False
                
        char_count += 1 # Account for the space separator in para_string
        
    # Quillbot filters out sequences of < 4 unchanged words
    l = -1
    i = 0
    while i < len(paraphrased_words):
        if l > 0:
            l -= 1
            paraphrased_words[i]["in_longest_substring"] = False
            i += 1
            continue
            
        if paraphrased_words[i].get("in_longest_substring"):
            # Check length of contiguous matching block
            count = 0
            curr = i
            while curr < len(paraphrased_words) and paraphrased_words[curr].get("in_longest_substring"):
                count += 1
                curr += 1
                
            if count >= 4:
                i += count
            else:
                l = count
                paraphrased_words[i]["in_longest_substring"] = False
                l -= 1
                i += 1
        else:
            i += 1
            
    return paraphrased_words

def make_underlines(original_sentence: str, paraphrased_words: list) -> list:
    """
    Identifies 'Structural Changes' (makeUnderlines in JS).
    
    JS Original Code:
    g(v, "makeUnderlines", (e, t) => {
        let a = ["a", "the", "of", "on", "is", "to", "with", "if", "and", "by", "it", "be", "are", "at", "from", "as"],
            s = e.replace(/([.?,*+^$[\]\\(){}|-])/g, " $1").split(" ").map(e => e.toLowerCase()),
            n = [], i = {};
        ...
        for (; _ > 0 && !((l += 1) > 2e4);) {
            let e = n[o], a = [e, e];
            if (1 !== e) { // Quillbot has a bug `1 !== e` instead of `-1 !== e`, we use != -1
                let e = n[o], s = o + 1;
                ...
    """
    stop_words = ["a", "the", "of", "on", "is", "to", "with", "if", "and", "by", "it", "be", "are", "at", "from", "as"]
    
    # Split by punctuations keeping them separate (mirrors JS replace/split logic)
    spaced_orig = re.sub(r'([.?,*+^$\[\]\\(){}|-])', r' \1', original_sentence)
    s_arr = [word.lower() for word in spaced_orig.split(" ") if word]
    
    n_arr = []
    i_map = {word: 0 for word in s_arr}
    
    for word_obj in paraphrased_words:
        word = word_obj.get("word", "").lower()
        r = -1
        
        start_idx = i_map.get(word, 0)
        if start_idx > 0 and word in s_arr[start_idx:]:
            r = s_arr.index(word, start_idx)
        elif word in s_arr:
            r = s_arr.index(word)
                
        n_arr.append(r)
        i_map[word] = max(r + 1, 0)

    r_arr = []
    o = 0
    _len = len(paraphrased_words)
    safety_counter = 0
    
    while _len > 0 and safety_counter <= 20000:
        safety_counter += 1
        e_val = n_arr[o]
        a = [e_val, e_val]
        
        if e_val != -1:
            e_curr = n_arr[o]
            start_s = o + 1
            for i in range(start_s, len(paraphrased_words)):
                t_val = n_arr[i]
                if t_val != -1:
                    if t_val == e_curr + 1:
                        a[1] = n_arr[i]
                        e_curr = t_val
                    else:
                        break
                        
        s_len = a[1] - a[0]
        o += s_len + 1
        _len -= s_len + 1
        r_arr.append(a)

    h = -1
    u = -1
    d = []
    c = 0
    
    for a_range in r_arr:
        s_val = a_range[0]
        i_val = a_range[1]
        
        if s_val == -1:
            c += 1
            continue
            
        if s_val > h:
            h = s_val
            u = i_val
            c += 1
            continue
            
        o_val = u - s_val
        if (i_val - s_val) == 0 and o_val > 10:
            c += 1
            continue
            
        _idx = n_arr.index(h)
        l_idx = n_arr.index(i_val)
        
        if (i_val - s_val) == 0 and paraphrased_words[l_idx]["word"].lower() in stop_words:
            c += 1
            continue
            
        p = 0
        while (c + 1) < len(r_arr) and r_arr[c + 1][0] == -1 and p <= 20000:
            l_idx += 1
            c += 1
            p += 1
            
        d.append([_idx, l_idx])
        c += 1

    for o in range(len(paraphrased_words)):
        is_under = False
        for a_range in d:
            if a_range[0] <= o <= a_range[1]:
                is_under = True
                break
        paraphrased_words[o]["is_structural_change"] = is_under
        
    return paraphrased_words

def process_legend(original_sentence: str, paraphrased_words: list) -> list:
    """
    Applies all three legend algorithms to the paraphrased words.
    """
    paraphrased_words = mark_different(original_sentence, paraphrased_words)
    paraphrased_words = mark_longest_substring(original_sentence, paraphrased_words)
    paraphrased_words = make_underlines(original_sentence, paraphrased_words)
    return paraphrased_words
