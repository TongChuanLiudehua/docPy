"""
    dependency
"""
import re, abc
from threading import Lock, Thread
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AbstractParser - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BasedObject:
    __module__ = abc.ABCMeta

    def __init__(self, name):
        self.name = name
        self.desc = ""
        self.linked_to = None

    def add_parent(self, parent):
        pass

    def add_child(self, child):
        """
        !! IMPORTANT
        child node must point to parent while adding a child node of this
        :param child:
        :return:
        """
        pass


class ModuleObject(BasedObject):
    def __init__(self, name):
        super().__init__(name)
        self.classes = []
        self.variables = []
        self.functions = []

    def add_parent(self, parent: BasedObject):
        pass  #

    def add_child(self, child: BasedObject):
        try:
            isinstance(child, (ClassObject, ModuleVariableObject, ModuleFunctionObject))
        except ValueError:
            return
        child.add_parent(self)  # auto link to parent while adding child
        if isinstance(child, ClassObject):
            self.classes.append(child)
        elif isinstance(child, ModuleVariableObject):
            self.variables.append(child)
        elif isinstance(child, ModuleFunctionObject):
            self.functions.append(child)


class ClassObject(BasedObject):
    def __init__(self, name):
        super().__init__(name)
        self.methods = []
        self.variables = []
        self.linked_to = []

    def add_parent(self, parent: ModuleObject):
        assert isinstance(parent, ModuleObject)
        self.linked_to.append(parent)
        #  parent.add_child(self) !
        #  !!important this is illegal, because when adding a relations, the parent will add
        # this child automatically by calling parent.add_child() in your code and doing this by yourself!

    def add_child(self, child: BasedObject):

        try:
            isinstance(child, (MemberVariableObject, ClassMethodObject))
        except ValueError:
            return

        child.add_parent(self)
        if isinstance(child, MemberVariableObject):
            self.variables.append(child)
        elif isinstance(child, ClassMethodObject):
            self.methods.append(child)


class DependencyObject(BasedObject):
    def __init__(self, name):
        super().__init__(name)
        self.deps = []


class VariableObject(BasedObject):
    __module__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)
        self.type = None

    def add_child(self, child):
        logging.error("variable object have no child!")
        raise TypeError


class MemberVariableObject(VariableObject):
    def __init__(self, name: str):
        super().__init__(name)
        self.linked_to = None  # must be a class object

    def add_parent(self, parent: ClassObject):
        try:
            assert isinstance(parent, ClassObject)
        except ValueError:
            return
        self.linked_to = parent
        # parent.variables.append(self)
        #  !!important this is illegal, because when adding a relations, the parent will add
        # this child automatically by calling parent.add_child() in your code and doing this by yourself!


class ModuleVariableObject(VariableObject):
    def __init__(self, name: str):
        super().__init__(name)
        self.linked_to = []  # a variable defined in a module may be used in other module

    def add_parent(self, parent: ModuleObject):
        try:
            assert isinstance(parent, ModuleObject)
        except ValueError:
            return
        self.linked_to.append(parent)
        # parent.variables.append(self)
        #  !!important this is illegal, because when adding a relations, the parent will add
        # this child automatically by calling parent.add_child() in your code and doing this by yourself!


class FunctionObject(BasedObject):
    __module__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)
        self.in_param = []
        self.out_type = ""

    def add_child(self, child):
        logging.error("function object have no child!")
        raise TypeError


class ModuleFunctionObject(FunctionObject):
    def __init__(self, name):
        super().__init__(name)
        self.linked_to = []

    def add_parent(self, parent: ModuleObject):
        try:
            assert isinstance(parent, ModuleObject)
        except ValueError:
            return
        self.linked_to.append(parent)
        # parent.add_child(self)
        #  !!important this is illegal, because when adding a relations, the parent will add
        # this child automatically by calling parent.add_child() in your code and doing this by yourself!


class ClassMethodObject(FunctionObject):
    def __init__(self, name):
        super().__init__(name)
        self.linked_to = None

    def add_parent(self, parent: ClassObject):
        try:
            assert isinstance(parent, ClassObject)
        except ValueError:
            return
        self.linked_to = parent
        # parent.add_child(self)
        #  !!important this is illegal, because when adding a relations, the parent will add
        # this child automatically by calling parent.add_child() in your code and doing this by yourself!


class AbstractSignalFunctional(object):

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

        self._class_set = {}
        self._module_set = {}
        self._variable_set = {}
        self._header_set = {}
        self._function_set = {}
        self._unresolved_relations = {}
        self._obj_set = {

            # name: []
        }

    def combine_to_tuple(self, key: str, string: str):
        for single in re.findall(self._patterns[key], string):
            if isinstance(single, tuple):
                yield single
            else:
                yield (single,)

    def __break_down(self, sp: str) -> tuple:
        return sp[:sp.find(":")].strip().upper(), [i.strip() for i in sp[sp.find(":") + 1:].split(",")]

    def __link(self, tgt, parents):
        for parent in parents:
            try:
                if len(self._obj_set[parent]) == 1:
                    self._obj_set[parent][0].add_child(tgt)
                    logging.info(
                        "link '{}' (type={})-> '{}' (type={})".format(tgt.name, tgt.__class__.__name__,
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
            except KeyError as e:
                self._unresolved_relations[tgt] = ModuleObject(parent)
        pass

    def link(self, tgt, parents):
        type, pts = self.__break_down(parents)
        if isinstance(tgt, ModuleObject):
            for parent in pts:
                if type == "M":
                    pass
                elif type == "LK":
                    pass
                logging.info("{} module do not necessary to have a parent.".format(tgt.name))
        if isinstance(tgt, ClassObject):
            for parent in pts:
                if type == "M":
                    try:
                        self._module_set[parent].classes.append(tgt)
                        tgt.linked_to = self._module_set[parent]
                        logging.info("link class '{}' -> module '{}'".format(tgt.name, parent))
                    except KeyError as e:
                        self._unresolved_relations[tgt] = ModuleObject(parent)
                        logging.info("unresolved relation between class '{}' -> module ''{}.".format(tgt.name, parent))
                else:
                    pass
        if isinstance(tgt, FunctionObject):
            for parent in pts:
                if type == "M":
                    try:
                        self._class_set[parent].methods.append(tgt)
                        tgt.linked_to = self._class_set[parent]
                        logging.info("link function '{}' -> class '{}'".format(tgt.name, parent))
                    except KeyError:
                        self._unresolved_relations[tgt] = ClassObject(parent)
                        logging.info("unresolved relation between method '{}' -> class ''{}.".format(tgt.name, parent))
                elif type == "LK":
                    try:
                        self._module_set[parent].functions.append(tgt)
                        tgt.linked_to = self._module_set[parent]
                        logging.info("link function '{}' -> module '{}'".format(tgt.name, parent))
                    except KeyError:
                        self._unresolved_relations[tgt] = ModuleObject(parent)
                        logging.info(
                            "unresolved relation between function '{}' -> module ''{}.".format(tgt.name, parent))
                else:
                    logging.error("suffix may be error, with suffix='{}'".format(type))
        if isinstance(tgt, VariableObject):
            for parent in pts:
                if type == "M":
                    try:
                        self._class_set[parent].variables.append(tgt)
                        tgt.linked_to = self._class_set[parent]
                        logging.info("link variable '{}' -> class '{}'".format(tgt.name, parent))
                    except KeyError:
                        self._unresolved_relations[tgt] = ClassObject(parent)
                        logging.info(
                            "unresolved relation between variable '{}' -> class ''{}.".format(tgt.name, parent))
                elif type == "LK":
                    try:
                        self._module_set[parent].variables.append(tgt)
                        tgt.linked_to = self._module_set[parent]
                        logging.info("link variable '{}' -> module '{}'".format(tgt.name, parent))
                    except KeyError:
                        self._unresolved_relations[tgt] = ModuleObject(parent)
                        logging.info(
                            "unresolved relation between variable '{}' -> module ''{}.".format(tgt.name, parent))
                else:
                    logging.error("suffix may be error, with suffix={}(type)".format(type))

    def link2(self):
        for tgt in self._unresolved_relations.keys():
            faker_parent = self._unresolved_relations[tgt]

            if isinstance(tgt, ClassObject):
                if faker_parent.name in self._module_set.keys():
                    self._module_set[faker_parent.name].classes.append(tgt)
                    logging.info("resolve a relation class '{}' -> module '{}'".format(tgt.name, faker_parent.name))
                    continue
                else:
                    logging.error("unresolved relations happened! class : {}'s Parent '{}' isn't a module"
                                  "\nclass '{}' no where to be linked!".format(tgt.name, faker_parent.name, tgt.name))
            if isinstance(tgt, VariableObject):
                if isinstance(faker_parent, ClassObject) and faker_parent.name in self._class_set.keys():
                    self._class_set[faker_parent.name].variables.append(tgt)
                    logging.info("resolve a relation variable '{}' -> class '{}'".format(tgt.name, faker_parent.name))
                elif isinstance(faker_parent, ModuleObject) and faker_parent.name in self._module_set.keys():
                    self._module_set[faker_parent.name].variables.append(tgt)
                    logging.info("resolve a relation variable '{}' -> module '{}'".format(tgt.name, faker_parent.name))
                else:
                    logging.error(
                        "unresolved relations happened! variable : {}'s Parent '{}' neither is a module or a class"
                        "\nvariable '{}' no where to be linked!".format(tgt.name, faker_parent.name, tgt.name))

            if isinstance(tgt, FunctionObject):
                if isinstance(faker_parent, ClassObject) and faker_parent.name in self._class_set.keys():
                    self._class_set[faker_parent.name].methods.append(tgt)
                    logging.info("resolve a relation method '{}' -> class '{}'".format(tgt.name, faker_parent.name))
                elif isinstance(faker_parent, ModuleObject) and faker_parent.name in self._module_set.keys():
                    self._module_set[faker_parent.name].functions.append(tgt)
                    logging.info("resolve a  relation function '{}' -> module '{}'".format(tgt.name, faker_parent.name))

                else:
                    logging.error(
                        "unresolved relations happened! function : {}'s Parent '{}' neither is a module or a class"
                        "\nfunction '{}' no where to be linked!".format(tgt.name, faker_parent.name, tgt.name))

                continue

    def __add_obj(self, name, obj):
        try:
            self._obj_set[name].append(obj)
        except KeyError:
            self._obj_set[name] = [obj]

    def func_go(self, *args, **kwargs):
        global target, name, func_in_param_list, func_out_param
        clx = ""
        desc = ""
        func_in_param_list = []
        func_out_param = ""
        for oi in args:
            try:
                result = self.combine_to_tuple(oi, kwargs["comment"])
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
                            self.__link(target, parents)  # result_tuple(parent) <- target
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

    def markdown_format(self):
        for md in self._module_set.keys():
            md_name = self._module_set[md].name
            md_desc = self._module_set[md].desc
            self.chunk += ToMarkdownSignalFunctional.H1 + " *Modules* {}\n".format(md_name)
            self.chunk += ToMarkdownSignalFunctional.Desc + "{}\n\n".format(md_desc.strip())
            self.chunk += ToMarkdownSignalFunctional.Bar + " \n"
            for var in self._module_set[md].variables:
                if var.linked_to is self._module_set[md]:
                    self.chunk += ToMarkdownSignalFunctional.H2 + " *Variable*  {}: ({})\n".format(var.name, var.type)
                    self.chunk += ToMarkdownSignalFunctional.Desc + "{}\n\n".format(var.desc)
                    self.chunk += ToMarkdownSignalFunctional.Bar + " \n"
            for func in self._module_set[md].functions:
                if func.linked_to is self._module_set[md]:
                    self.chunk += ToMarkdownSignalFunctional.H2 + "*Function*  {}\n".format(func.name)
                    for param in func.in_param:
                        self.chunk += ToMarkdownSignalFunctional.H4 + "*param*  ({}) {}:\n".format(param[0], param[1])
                        self.chunk += ToMarkdownSignalFunctional.Desc + "{}\n\n".format(param[2])
                    self.chunk += ToMarkdownSignalFunctional.H4 + "*return*  {}\n".format(func.out_type)
                    self.chunk += ToMarkdownSignalFunctional.Desc + "{}\n\n".format(func.desc)
                    self.chunk += ToMarkdownSignalFunctional.Bar + " \n"
            for cls in self._module_set[md].classes:
                self.chunk += ToMarkdownSignalFunctional.H2 + " *Class*  {}\n".format(cls.name)
                for var in cls.variables:
                    self.chunk += ToMarkdownSignalFunctional.H3 + " *var*  {}: *({})*\n".format(var.name, var.type)
                    self.chunk += ToMarkdownSignalFunctional.Desc + "{}\n\n".format(var.desc)
                    self.chunk += ToMarkdownSignalFunctional.Bar + " \n"
                for method in cls.methods:
                    self.chunk += ToMarkdownSignalFunctional.H3 + " *method*  {}\n".format(method.name)
                    for param in method.in_param:
                        self.chunk += ToMarkdownSignalFunctional.H4 + "*param*  ({}) {}:\n".format(param[0], param[1])
                        self.chunk += ToMarkdownSignalFunctional.Desc + "{}\n\n".format(param[2])
                    self.chunk += ToMarkdownSignalFunctional.H4 + "*return* {}\n".format(method.out_type)
                    self.chunk += ToMarkdownSignalFunctional.Desc + "{}\n\n".format(method.desc)
                    self.chunk += ToMarkdownSignalFunctional.Bar + " \n"
        self.dump(self.chunk, r"E:\file\pyProj\docPy\test\targetfile")
