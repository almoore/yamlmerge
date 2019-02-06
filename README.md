YAML MERGE
==========

# Purpose
This package is meant to make merging of yaml file much easier. For example
with the kubectl config files for many environments you can have them stored
all in one directory and then merge them into one file that will be much
simpler to maintain.

# Install


Install from source

```
pip install git+https://github.com/almoore/yamlmerge.git
```

Or clone and install from local repo.

```
git clone https://github.com/almoore/yamlmerge.git
pip install ./yamlmerge
```

# Usage

## All files in a directory ##

Yamlmerge takes all the aruments that are given as input files and outputs the
result.

So, you can have then redirect the output to a file the write that.

```
yamlmerge ~/.kube/config.d/* > ~/.kube/config
```
