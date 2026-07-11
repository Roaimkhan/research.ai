from __future__ import annotations

MEMORY_TOOLS = [
	{
		"type": "function",
		"function": {
			"name": "add_memory",
			"description": "Call when the user states a new fact, preference, or event worth remembering.",
			"parameters": {
				"type": "object",
				"properties": {
					"fact": {
						"type": "string",
						"description": "The fact, preference, or event to store.",
					},
					"entity_tags": {
						"type": "array",
						"items": {"type": "string"},
						"description": "Tags for the people, places, projects, or topics involved.",
					},
					"type": {
						"type": "string",
						"enum": ["episodic", "semantic", "procedural"],
						"description": "Memory category to store the fact under.",
					},
					"confidence": {
						"type": "number",
						"minimum": 0,
						"maximum": 1,
						"description": "How confident the model is that this should be stored as memory.",
					},
				},
				"required": ["fact", "entity_tags", "type", "confidence"],
				"additionalProperties": False,
			},
		},
		"x_risk_level": "low",
	},
	{
		"type": "function",
		"function": {
			"name": "update_memory",
			"description": "Call when an existing memory should be corrected, refined, or superseded with newer information.",
			"parameters": {
				"type": "object",
				"properties": {
					"memory_id": {
						"type": "string",
						"description": "Identifier of the memory to update.",
					},
					"fact": {
						"type": "string",
						"description": "The revised memory content to store.",
					},
					"confidence": {
						"type": "number",
						"minimum": 0,
						"maximum": 1,
						"description": "Confidence that this update reflects the best current version of the memory.",
					},
				},
				"required": ["memory_id", "fact", "confidence"],
				"additionalProperties": False,
			},
		},
		"x_risk_level": "medium",
	},
	{
		"type": "function",
		"function": {
			"name": "delete_memory",
			"description": "Call only when the user explicitly requests removal of a memory or when a memory must be deleted for safety, privacy, or obvious obsolescence.",
			"parameters": {
				"type": "object",
				"properties": {
					"memory_id": {
						"type": "string",
						"description": "Identifier of the memory to delete.",
					},
					"reason": {
						"type": "string",
						"description": "Reason the memory should be deleted.",
					},
				},
				"required": ["memory_id", "reason"],
				"additionalProperties": False,
			},
		},
		"x_risk_level": "high",
	},
	{
		"type": "function",
		"function": {
			"name": "search_memory",
			"description": "Call when the user asks to recall, find, or retrieve stored memories relevant to a query.",
			"parameters": {
				"type": "object",
				"properties": {
					"query": {
						"type": "string",
						"description": "Search text describing the memory to retrieve.",
					},
					"top_k": {
						"type": "integer",
						"minimum": 1,
						"default": 5,
						"description": "Maximum number of memories to return.",
					},
					"memory_type": {
						"type": "string",
						"enum": ["episodic", "semantic", "procedural"],
						"description": "Optional filter to restrict results to one memory type.",
					},
				},
				"required": ["query"],
				"additionalProperties": False,
			},
		},
		"x_risk_level": "low",
	},
]
