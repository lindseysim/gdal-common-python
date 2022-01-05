class Field:
    '''
    Simple class for a 'field' type of feature dataset. Should not be constructed directly, should be returned through
    functions in `fields` module.
    :property is_fid: (boolean) Whether this represents special case of FID.
    :property defn: (ogr.FieldDefn) Field as ogr.FieldDefn instance.
    :property name: (str) Field name.
    :property index: (int) Field index position in layer, or -1 if not present.
    :property type: (str) Field data type as string name.
    :property width: (int) Field width, if specified, or 0.
    :property precision: (int) Field precision, if specified, or 0.
    '''
    def __init__(self, is_fid=False, fdefn=None, field_name=None, lyr_defn=None, must_exist=True):
        self.is_fid    = False
        self.defn      = None
        self.name      = ""
        self.index     = -1
        self.type      = None
        self.width     = 0
        self.precision = 0
        if is_fid:
            self.name = "FID"
            self.is_fid = True
        else:
            if not fdefn:
                assert field_name
                assert lyr_defn
                self.index = lyr_defn.GetFieldIndex(field_name)
                if self.index < 0:
                    if must_exist:
                        raise Exception("Field ({0}) does not exist".format(field_name))
                else:
                    fdefn = lyr_defn.GetFieldDefn(self.index)
            if fdefn:
                self.defn      = fdefn
                self.name      = fdefn.GetName()
                self.type      = fdefn.GetFieldTypeName(fdefn.GetType())
                self.width     = fdefn.GetWidth()
                self.precision = fdefn.GetPrecision()
                if self.index < 0 and lyr_defn:
                    self.index = lyr_defn.GetFieldIndex(fdefn.GetName())
            if must_exist and (self.index < 0 or not self.defn):
                raise Exception("Field ({0}) does not exist".format(self.name))
