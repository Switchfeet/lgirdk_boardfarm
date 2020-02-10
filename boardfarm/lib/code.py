import re
import six
import subprocess

def get_all_classes_from_code(directories, debug=False):
    '''
    Uses 'grep' to find all files of type '.py' in the given directories.
    Then parses those files to return a dict where:
         * keys = class names
         * values = list with "parent class name" and "grandparent class name"
    '''
    if debug:
        print("Searching for classes in:")
    raw_text = []
    for d in directories:
        if debug:
            print(d)
        cmd = "grep -E '^class' %s" % d
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            raw_text.append(result)
        except subprocess.CalledProcessError:
            if debug:
                print("Warning: No tests found in %s" % d)
    raw_text = "".join(six.text_type(raw_text))
    # Create a list of tuples (classname, parent_classname)
    result = re.findall('class\s(\w+)\(([\w\.]+)\):', raw_text)
    #print(result)
    # Convert that list into a Python dict such that
    #    {"classname1": [parent_classname1,],
    #     "classname2": [parent_classname2,], ... etc}
    # Because we will add parents to that list.
    all_classes = dict([(x[0], [x[1],]) for x in result])
    # Add grandparent class
    for name in all_classes:
        parent = all_classes[name][0]
        if parent not in all_classes:
            continue
        grandparent = all_classes[parent][0]
        all_classes[name].append(grandparent)
    if debug:
        print("Found %s python classes." % len(all_classes))
        #for name in sorted(all_classes):
        #    print("%30s: %s" % (name, ", ".join(all_classes[name])))
    return(all_classes)

def changed_classes(directories, start, end, debug=False):
    '''
    Return names of all changed classes in a "git diff".
    '''
    if debug:
        print("\nSearching for differences:")
    result = {}
    for d in directories:
        try:
            cmd = "git --git-dir %s diff %s..%s -U0" % (d, start, end)
            if debug:
                print(cmd)
            diff = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            result.update(dict(re.findall('class\s(\w+)\(([\w\.]+)\):', six.text_type(diff))))
        except subprocess.CalledProcessError:
            if debug:
                print("Warning: git diff command failed in %s" % d)
    if debug:
        print("\nAll directly changed classes from %s to %s:" % (start, end))
        for name in sorted(result):
            print("  %s : %s" % (name, result[name]))
    return result

def get_features(directories, start, end, debug=False):
    '''
    Return the list of words after 'Features:' in git log messages.
    '''
    if debug:
        print("\nSearching for 'Features' in git log:")
    result = []
    for d in directories:
        try:
            cmd = "git --git-dir %s log %s..%s" % (d, start, end)
            if debug:
                print(cmd)
            text = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            result += re.findall('Features:\s(\w+)', six.text_type(text))
        except subprocess.CalledProcessError:
            if debug:
                print("Warning: git log command failed in %s" % d)
    if debug:
        print("\nFeatures requested in git log from %s to %s:" % (start, end))
        print(" ".join(set(result)))
    return result