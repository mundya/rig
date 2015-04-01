'Exceptions which placers can throw to indicate standard types of problem.\n'
class InsufficientResourceError(Exception):'Indication that a process failed because adequate resources were not\n    available in the machine.\n    ';pass
class InvalidConstraintError(Exception):'Indication that a process failed because an impossible constraint was\n    given.\n    ';pass
class MachineHasDisconnectedSubregion(Exception):'Some part of the machine has no paths connecting it to the rest of the\n    machine.\n    ';pass
