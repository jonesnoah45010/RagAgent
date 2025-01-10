from local_semantic_db import local_semantic_db
from local_sql_db import local_sql_db
from semantic_text_splitter import text_splitter
import uuid

class semantic_sql_db:
	def __init__(self, sql_db_path="example_db/sql_db", semantic_db_dir="example_db/semantic_db"):
		"""
		description:
			Object that interfaces betweeen a local sql database and local chroma semantic database.
			This creates a seemless database that can run semantic queries and SQL queries.
		params:
			sql_db_path: string: path to where to save SQL database files
			semantic_db_dir: string: path to where to save the persistant chromadb directory
		attributes:
			sql_db: local_sql_db instance: object managing local sql database
			semantic_db: local_semantic_db instance: object managing local chroma semantic database
			table_name: string: name of the sql table / chroma database collection the object is currently pointing to
			unique_id_field: string or int: column name of the unique identifier in the sql database that will also be used as the unique text_id in the semantic database
			table_sql_schema: dict: dictionary representation of the schema for the table currently pointed to by the object
			semantic_search_field: string: column name of the field in the sql database that has an associated value in the semantic database, allowing it to be queried semantically
		returns:
			semantic_sql_db object instantiation
		example:
			db = semantic_sql_db()
			my_db = semantic_sql_db("Users/your_usersname/your_project/my_sql_db","Users/your_usersname/your_project/my_semantic_db")
		"""
		self.sql_db = local_sql_db(sql_db_path)
		self.semantic_db = local_semantic_db(semantic_db_dir,collection_name=None)
		self.table_name = None
		self.unique_id_field = None
		self.table_sql_schema = None
		self.semantic_search_field = None


	def set_table(self, table_name, semantic_search_field, unique_id_field, table_sql_schema=None):
		"""
		description:
			sets table self is currently pointing to or creates a new table
		params:
			table_name: string: name of table you want to point to
			semantic_search_field: string: column name in table that will be looked at for semantic queries
			unique_id_field: string: column name in table that is the unique identifier
			table_sql_schema: dict: optional representation of the sql table schema if you are creating a new table
		returns:
			None
		example:
			db = semantic_sql_db()
			new_table_schema = {
				"id": "TEXT PRIMARY KEY", # unique id field
				"name": "TEXT",
				"description": "TEXT NOT NULL", # semantic search field
				"category": "TEXT",
				"page_number": "INTEGER",
				"created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
			}
			db.set_table(table_name="users",semantic_search_field="description",unique_id_field="id",table_sql_schema=new_table_schema)

		"""
		if semantic_search_field not in table_sql_schema:
			raise ValueError("table_sql_schema must contain semantic_search_field")
		if unique_id_field not in table_sql_schema:
			raise ValueError("table_sql_schema must contain unique_id_field")
		if table_sql_schema is not None:
			table_created = self.sql_db.create_table(table_name,table_sql_schema)
		self.semantic_db.set_collection(table_name)
		self.table_name = table_name
		if table_sql_schema is not None:
			self.table_sql_schema = table_sql_schema
		else:
			self.table_sql_schema = self.sql_db.get_schema(self.table_name)
		self.semantic_search_field = semantic_search_field
		self.unique_id_field = unique_id_field



	def chunk_text_for_insert(self, text, metadata=None, max_sentences_per_chunk=10):
		"""
		description:
			Splits a given text into smaller chunks of a specified number of sentences
			and prepares metadata for insertion into the database. Each chunk will 
			have the semantic search field auto-populated and metadata associated 
			with it.

		params:
			text: string: The full text that needs to be split into chunks.
			max_sentences_per_chunk: int: Maximum number of sentences allowed in each chunk.
			metadata: dict: Metadata that will be associated with each chunk. It should 
						   align with self.table_sql_schema but should not include 
						   self.unique_id_field or self.semantic_search_field as 
						   these will be auto-generated.

		returns:
			list: A list of dictionaries where each dictionary represents a row that 
				  can be passed to the self.insert(data) method. Each dictionary 
				  includes metadata and the corresponding chunked text.

		example:
			db = semantic_sql_db()
			text = "This is sentence one. This is sentence two. This is sentence three."
			metadata = {
				"name": "Sample Text",
				"category": "Example",
				"page_number": 1
			}
			chunked_data = db.chunk_text_for_insert(
				text=text, 
				max_sentences_per_chunk=2, 
				metadata=metadata
			)
			# chunked_data will contain:
			# [
			#	 {"name": "Sample Text", "category": "Example", "page_number": 1, "description": "This is sentence one. This is sentence two."},
			#	 {"name": "Sample Text", "category": "Example", "page_number": 1, "description": "This is sentence three."}
			# ]
		"""
		chunks = text_splitter(text, max_sentences_per_chunk)
		insertable = []
		for c in chunks:
			row = eval(repr(metadata))
			row[self.semantic_search_field] = c
			insertable.append(row)
		return insertable





	def insert(self, data, check_validity=False):
		"""
		description:
			inserts data into sql and semantic databases
		params:
			data: list of dictionaries: data to be inserted into databases
			check_validity: boolearn: check data for validity or not
		returns:
			None
		example:
			db = semantic_sql_db()
			sample_data = [
				{"name": "Sports Article", "description": "An article about football and soccer", "category": "sports", "page_number": 12},
				{"name": "Sports Article 2", "description": "An article about baseball", "category": "sports", "page_number": 13},
				{"name": "Science News", "description": "A detailed explanation of quantum mechanics", "category": "science", "page_number": 45},
				{"name": "Cooking Tips", "description": "A guide to making the perfect lasagna", "category": "cooking", "page_number": 30},
				{"name": "Travel Guide", "description": "Exploring the beaches in Hawaii", "category": "travel", "page_number": 70},
				{"name": "Fitness Tips", "description": "Advice on cardio workouts and staying fit", "category": "fitness", "page_number": 15},
			]
			db.insert(sample_data)
		"""
		if check_validity:
			for d in data:
				if not all(key in self.table_sql_schema for key in d):
					raise ValueError("data should be a list of dicts with keys that match the table_sql_schema")


		# generate uuid unique_id_field if one isn't present already
		unique_ids = []
		if any(self.unique_id_field not in entry.keys() or entry[self.unique_id_field] is None for entry in data):
			for d in data:
				uid = str(uuid.uuid4())
				d[self.unique_id_field] = uid
				unique_ids.append(uid)

		if unique_ids == []:
			for d in data:
				unique_ids.append(d[self.unique_id_field])

		self.sql_db.insert_data(table_name=self.table_name, data=data)

		def fields_were_generated():
			fields = self.table_sql_schema.keys()
			if fields != data[0].keys():
				return True
			return False

		if fields_were_generated():
			ids = tuple(unique_ids)
			if len(ids) == 1:
				ids = str(ids).replace(",","")
			else:
				ids = str(ids)
			q = "SELECT * FROM " + str(self.table_name) + " WHERE " + str(self.unique_id_field) + " IN " + ids + ";"
			data = self.sql_db.query_data(query=q)

		texts=[]
		metadatas=[]
		text_ids=[]
		insert_to_sql = []
		for d in data:
			d_copy = eval(repr(d))
			if self.unique_id_field not in d_copy.keys() or d_copy[self.unique_id_field] is None:
				d_copy[self.unique_id_field] = str(uuid.uuid4())
			semantic_search_value = d[self.semantic_search_field]
			insert_to_sql.append(d_copy)
			d_copy2 = eval(repr(d_copy))
			del d_copy2[self.semantic_search_field]
			texts.append(semantic_search_value)
			metadatas.append(d_copy2)
			try:
				text_ids.append(d[self.unique_id_field])
			except:
				pass

		if text_ids == []:
			text_ids = None

		self.semantic_db.batch_insert(texts=texts,metadatas=metadatas,text_ids=text_ids)

		return unique_ids



	def insert_text_in_chunks(self, text, metadata=None, max_sentences_per_chunk=10, check_validity=False):
		data = self.chunk_text_for_insert(text, metadata=metadata, max_sentences_per_chunk=max_sentences_per_chunk)
		return self.insert(data,check_validity=check_validity)

	
	def get(self, unique_id):
		"""
		description:
			fetches entire row of data from the sql database based on the given unique_id or list/tuple of unique_ids
		params:
			unique_id: string or int, or list/tuple of strings or ints: the unique id or list/tuple of unique ids for the data you want to fetch
		returns:
			list of dictionaries representing the fetched data
		example:
			db = semantic_sql_db()
			db.insert(data={"text":"hi there","source":"book","id":1},check_validity=True)
		"""
		if type(unique_id) not in [list,tuple]:
			return self.sql_db.query_data("SELECT * FROM " + self.table_name + " WHERE " + self.unique_id_field + " = ?",(unique_id,))
		else:
			return self.sql_db.query_data("SELECT * FROM " + self.table_name + " WHERE " + self.unique_id_field + " in ?",tuple(unique_id))



	def hybrid_query(self, query_text, top_k=3, sql_where=None):
		"""
		description:
			runs a hybric semantic search and sql query for entries sematically similar to text but limited based on an sql where clause
		params:
			text: string: text for which you want to find entries that are semantically similar to.
			top_k: int: desired number of results.
			sql_where: string: chunk of valid SQL that would go after the WHERE in an SQL query. Should use logic to narrow your results.
		returns:
			list of dictionaries representing results
		example:
			db = semantic_sql_db()
			text = "having to do with sports"
			results = db.semantic_query(text,top_k=5,sql_where="page_number > 10 and page_number < 100")
		"""
		q = "SELECT " + str(self.unique_id_field) + " FROM " + str(self.table_name) + " WHERE " + sql_where + ";"
		ids = self.sql_db.query_data(q,return_dict_list=False)
		ids_list = []
		for i in ids:
			ids_list.append(i[0])

		semantic_query_result = self.semantic_db.query(
				query_text=query_text,
				top_k=top_k,
				where={self.unique_id_field: {"$in": ids_list}}  # Use $in to filter by multiple values
			)

		return semantic_query_result

	











if __name__ == "__main__":


	# Instantiate the semantic_sql_db class
	db = semantic_sql_db(sql_db_path="test_db/test_sql_db", semantic_db_dir="test_db/test_semantic_db")

	# Define the table schema
	# unique id field and semantic search field must be TEXT
	new_table_schema = {
		"id": "TEXT PRIMARY KEY", # unique id field
		"name": "TEXT",
		"description": "TEXT NOT NULL", # semantic search field
		"category": "TEXT",
		"page_number": "INTEGER",
		"created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
	}

	# Set up a new table for our hybrid database
	db.set_table(
		table_name="documents",
		semantic_search_field="description",  # This field will be queried semantically
		unique_id_field="id", # this field will be the unique identifier
		table_sql_schema=new_table_schema
	)


	# Insert sample data into the database
	sample_data = [
		{"name": "Sports Article", "description": "An article about football and soccer", "category": "sports", "page_number": 12},
		{"name": "Sports Article 2", "description": "An article about baseball", "category": "sports", "page_number": 13},
		{"name": "Science News", "description": "A detailed explanation of quantum mechanics", "category": "science", "page_number": 45},
		{"name": "Cooking Tips", "description": "A guide to making the perfect lasagna", "category": "cooking", "page_number": 30},
		{"name": "Travel Guide", "description": "Exploring the beaches in Hawaii", "category": "travel", "page_number": 70},
		{"name": "Fitness Tips", "description": "Advice on cardio workouts and staying fit", "category": "fitness", "page_number": 15},
	]

	db.insert(sample_data, check_validity=True)


	# Perform a hybrid query: semantic search filtered by SQL conditions
	query_text = "information about physical activity"  # The semantic query text
	top_k = 3
	sql_where = "page_number > 10 AND page_number < 50"  # SQL filter condition

	# Perform the query
	results = db.hybrid_query(query_text=query_text, top_k=top_k, sql_where=sql_where)

	# Print results
	print("Hybrid Query Results:")
	for result in results:
		print(result)
























