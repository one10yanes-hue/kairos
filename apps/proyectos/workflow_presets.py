"""Presets de flujo de trabajo compartidos para el modulo proyectos.
   Fuente unica de verdad para transiciones y roles requeridos por preset."""

PRESETS = {
    "simple": {
        "tarea": [
            ("pendiente", "en_curso"), ("pendiente", "cancelada"), ("pendiente", "bloqueada"),
            ("en_curso", "pausada"), ("en_curso", "finalizada"), ("en_curso", "cancelada"),
            ("en_curso", "bloqueada"),
            ("pausada", "en_curso"), ("pausada", "finalizada"), ("pausada", "cancelada"),
            ("bloqueada", "en_curso"), ("bloqueada", "cancelada"),
            ("finalizada", "revision"),
            ("revision", "finalizada"), ("revision", "pendiente"),
        ],
        "historia": [
            ("backlog", "sprint_backlog"), ("sprint_backlog", "en_progreso"),
            ("en_progreso", "done"), ("sprint_backlog", "backlog"),
            ("done", "backlog"),
        ],
        "incidencia": [
            ("abierta", "triaged"), ("abierta", "en_progreso"), ("abierta", "cerrada"),
            ("abierta", "duplicada"),
            ("triaged", "en_progreso"), ("triaged", "cerrada"),
            ("en_progreso", "resuelta"), ("en_progreso", "cerrada"),
            ("resuelta", "cerrada"),
            ("cerrada", "abierta"),
            ("duplicada", "abierta"),
        ],
    },
    "revision": {
        "tarea": [
            ("pendiente", "en_curso"), ("pendiente", "cancelada"), ("pendiente", "bloqueada"),
            ("en_curso", "pausada"), ("en_curso", "finalizada"), ("en_curso", "cancelada"),
            ("en_curso", "bloqueada"),
            ("pausada", "en_curso"), ("pausada", "finalizada"), ("pausada", "cancelada"),
            ("bloqueada", "en_curso"), ("bloqueada", "cancelada"),
            ("finalizada", "revision"),
            ("revision", "finalizada"), ("revision", "pendiente"),
        ],
        "historia": [
            ("backlog", "sprint_backlog"), ("sprint_backlog", "en_progreso"),
            ("en_progreso", "revision"), ("revision", "done"),
            ("revision", "en_progreso"), ("sprint_backlog", "backlog"),
            ("done", "backlog"),
        ],
        "incidencia": [
            ("abierta", "triaged"), ("abierta", "en_progreso"), ("abierta", "cerrada"),
            ("abierta", "duplicada"),
            ("triaged", "en_progreso"), ("triaged", "cerrada"),
            ("en_progreso", "resuelta"), ("en_progreso", "cerrada"),
            ("resuelta", "cerrada"),
            ("cerrada", "abierta"),
            ("duplicada", "abierta"),
        ],
    },
}

ROLES_POR_PRESET = {
    "simple": ["lider", "ejecutor"],
    "revision": ["lider", "responsable", "ejecutor", "revisor", "aprobador"],
    "completo": ["lider", "responsable", "ejecutor", "revisor", "aprobador", "observador"],
}

ROLES_REQUERIDOS = {
    "simple": ["lider", "ejecutor"],
    "revision": ["lider", "ejecutor", "revisor", "aprobador"],
    "completo": ["lider", "ejecutor", "revisor", "aprobador"],
}
