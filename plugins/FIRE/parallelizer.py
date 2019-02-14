
def jobs(self):
    import glob, os
    files = glob.glob(os.path.join(self.data_folder,"*.gz"))
    #self.logger.debug("Parallelized upload for files: %s" % files)
    return [(f,) for f in files]
