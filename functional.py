"""
    dependency
"""
import re, abc
from threading import Lock, Thread
import logging

from codeObject import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AbstractParser - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AbstractSignalFunctional(object):
    __module__ = abc.ABCMeta

    def __init__(self):

        self._patterns = {
            "func_name_pat": re.compile("@: *([a-zA-Z_0-9]+) *\n"),
            "class_name_pat": re.compile("&: *class *(.*?) *\n"),
            "var_name_pat": re.compile("[vV]ar: *\((.*?)\) *(.*?) *\n"),
            "in_param_pat": re.compile(
                ">: *\( *(?P<type>[a-zA-Z_0-9:]+) *\) *(?P<name>[a-zA-Z_0-9]+) *: *(?P<desc>.*?) *\n"),
            "out_param_pat": re.compile("<: *\( *(?P<type>[a-zA-Z_0-9:]+) *\) *\n"),
            "desc_pat": re.compile("\$:(.*?)\n"),
            "header_pat": re.compile("!: *(.*?) *\n"),
            "dep_pat": re.compile("#: *(.*?) *\n"),
            "link_pat": re.compile(" (?:(?:[ToOt]+)|(?:[LKk]+)|(?:[Mm])): *.*? *\n")
        }

        self._unresolved_relations = {}
        self._obj_set = {

            # name: []
        }

    def __combine_to_tuple(self, key: str, string: str):
        for single in re.findall(self._patterns[key], string):
            if isinstance(single, tuple):
                yield single
            else:
                yield (single,)

    def __break_down(self, sp: str) -> tuple:
        return sp[:sp.find(":")].strip().upper(), [i.strip() for i in sp[sp.find(":") + 1:].split(",")]

    def __find_parent_to_add_tgt(self, tgt, parent, header):
        try:
            if len(self._obj_set[parent]) == 1:
                self._obj_set[parent][0].add_child(tgt)
                logging.info(
                    "{} link '{}' (type='{}') -> '{}' (type={})".format(header, tgt.name, tgt.__class__.__name__,
                                                                        self._obj_set[parent][0].name,
                                                                        self._obj_set[parent][0].__class__.__name__))
            else:
                for sub in self._obj_set[parent]:
                    try:
                        sub.add_child(tgt)
                        logging.info(
                            "link '{}' (type='{}') -> '{}' (type={})".format(tgt.name, tgt.__class__.__name__,
                                                                             sub.name,
                                                                             sub.__class__.__name__))
                        break
                    except ValueError:
                        return
                    except TypeError as e:
                        return
                    except Exception as e:
                        logging.fatal(e)
        except KeyError:
            raise KeyError

    def __add_obj(self, name, obj):
        try:
            self._obj_set[name].append(obj)
        except KeyError:
            self._obj_set[name] = [obj]

    def link(self, tgt, parents):
        for parent in parents:
            try:
                self.__find_parent_to_add_tgt(tgt, parent, "")
            except KeyError:
                if isinstance(tgt.linked_to, list):
                    try:
                        self._unresolved_relations[tgt].append(parent)
                    except KeyError:
                        self._unresolved_relations[tgt] = [parent]
                    logging.info("unresolved link: '{}' "
                                 "(type={}) -> '{}' (type=unknown)".format(tgt.name, tgt.__class__.__name__, parent))

    def link2(self):
        for tgt in self._unresolved_relations.keys():
            for parent in self._unresolved_relations[tgt]:
                try:
                    self.__find_parent_to_add_tgt(tgt, parent, "resolve")
                except KeyError:
                    logging.error(
                        "unresolved relations happened!  {}' -> '{}' . '{}' not find!".format(tgt.name, parent, parent))

    def func_go(self, *args, **kwargs):
        global target, name, func_in_param_list, func_out_param
        clx = ""
        desc = ""
        func_in_param_list = []
        func_out_param = ""
        for oi in args:
            try:
                result = self.__combine_to_tuple(oi, kwargs["comment"])
                while True:
                    try:
                        # TODO refactor
                        result_tuple = next(result)
                        if oi == "class_name_pat":
                            target = ClassObject(result_tuple[0])
                            self.__add_obj(target.name, target)
                            logging.info("create a new class '{}'".format(target.name))
                        elif oi == "func_name_pat":
                            # delay until link
                            name = result_tuple
                            clx = "func"
                        elif oi == "var_name_pat":
                            # delay until link
                            name = result_tuple
                            clx = "var"
                        elif oi == "header_pat":
                            target = ModuleObject(result_tuple[0])
                            self.__add_obj(target.name, target)
                            logging.info("create a new module '{}'".format(target.name))
                        elif oi == "desc_pat":
                            desc += result_tuple[0]
                        elif oi == "link_pat":
                            type, parents = self.__break_down(result_tuple[0])
                            if clx == "func":
                                if type == "M":
                                    target = ClassMethodObject(name[0])
                                elif type == "LK":
                                    target = ModuleFunctionObject(name[0])
                                target.in_param.extend(func_in_param_list)
                                target.out_type = func_out_param
                                self.__add_obj(target.name, target)
                                logging.info("create a new function '{}'".format(target.name))
                            elif clx == "var":
                                if type == "M":
                                    target = MemberVariableObject(name[1])
                                elif type == "LK":
                                    target = ModuleVariableObject(name[1])
                                target.type = name[0]
                                self.__add_obj(target.name, target)
                                logging.info("create a new variable '{}'".format(target.name))
                            self.link(target, parents)  # result_tuple(parent) <- target
                            clx = ""
                        elif oi == "in_param_pat":
                            func_in_param_list.append(result_tuple)
                        elif oi == "out_param_pat":
                            func_out_param = result_tuple[0]
                        else:
                            break
                    except StopIteration:
                        break
            except KeyError as e:
                logging.fatal(e)
        target.desc = desc

    def dump(self, info, path):
        pass


class SynSignalFunctional(AbstractSignalFunctional):
    def __init__(self):
        super().__init__()
        self.file_lock = Lock()

    def dump(self, info, path):
        self.file_lock.acquire()
        with open(path, "a") as f:
            f.write(info)
        self.file_lock.release()


class ToMarkdownSignalFunctional(SynSignalFunctional):
    H1 = "# "
    H2 = "## "
    H3 = "### "
    H4 = "#### "
    Bar = " --- "
    Desc = "\n"

    def __init__(self):
        super().__init__()
        self.chunk = ""
        self.mods = []

    def transform_to_md(self):
        self.mods = [mod[0] for mod in self._obj_set.values() if isinstance(mod[0], ModuleObject)]

        for mod in self.mods:
            print("module: " + mod.name)
            for cls in mod.classes:
                for parent in cls.linked_to:
                    if parent is mod:
                        print(mod.name + "::" + "class:" + cls.name)
                        for var in cls.variables:
                            print(cls.name + "::", var.name, var.type)
                        for mth in cls.methods:
                            print(cls.name + "::", mth.name)
            for var in mod.variables:
                if isinstance(var, ModuleVariableObject):
                    for parent in var.linked_to:
                        if parent is mod:
                            print(mod.name + "::", var.name, var.type)
            for func in mod.functions:
                if isinstance(func, ModuleFunctionObject):
                    for parent in func.linked_to:
                        if parent is mod:
                            print(mod.name + "::", func.name)
