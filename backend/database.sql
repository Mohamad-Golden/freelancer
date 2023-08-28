CREATE TABLE technology (
        title VARCHAR NOT NULL, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        id SERIAL NOT NULL, 
        slug VARCHAR(30) NOT NULL, 
        PRIMARY KEY (id), 
        UNIQUE (title)
)

CREATE TABLE plan (
        id SERIAL NOT NULL, 
        title VARCHAR NOT NULL, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        duration_day INTEGER, 
        offer_number INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        UNIQUE (title)
)

CREATE TABLE role (
        id SERIAL NOT NULL, 
        title VARCHAR NOT NULL, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        PRIMARY KEY (id)
)


CREATE TABLE status (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        id SERIAL NOT NULL, 
        title VARCHAR NOT NULL, 
        PRIMARY KEY (id), 
        UNIQUE (title)
)


CREATE TABLE "user" (
        email VARCHAR NOT NULL, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        id SERIAL NOT NULL, 
        description VARCHAR, 
        name VARCHAR, 
        id_number VARCHAR(10), 
        age INTEGER, 
        offer_left INTEGER NOT NULL, 
        plan_id INTEGER, 
        plan_expire_at TIMESTAMP WITHOUT TIME ZONE, 
        hashed_password VARCHAR(32), 
        role_id INTEGER, 
        is_verified BOOLEAN NOT NULL, 
        is_email_verified BOOLEAN NOT NULL, 
        is_superuser BOOLEAN NOT NULL, 
        PRIMARY KEY (id), 
        UNIQUE (email), 
        FOREIGN KEY(plan_id) REFERENCES plan (id), 
        FOREIGN KEY(role_id) REFERENCES role (id)
)


CREATE TABLE usertechnology (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        technology_id INTEGER NOT NULL, 
        user_id INTEGER NOT NULL, 
        PRIMARY KEY (technology_id, user_id), 
        FOREIGN KEY(technology_id) REFERENCES technology (id), 
        FOREIGN KEY(user_id) REFERENCES "user" (id)
)


CREATE TABLE sampleproject (
        id SERIAL NOT NULL, 
        title VARCHAR NOT NULL, 
        description VARCHAR, 
        link VARCHAR, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        user_id INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(user_id) REFERENCES "user" (id)
)


CREATE TABLE education (
        id SERIAL NOT NULL, 
        institution_name VARCHAR NOT NULL, 
        major VARCHAR NOT NULL, 
        started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
        finished_at TIMESTAMP WITHOUT TIME ZONE, 
        in_progress BOOLEAN, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        user_id INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(user_id) REFERENCES "user" (id)
)


CREATE TABLE experience (
        id SERIAL NOT NULL, 
        company_name VARCHAR NOT NULL, 
        in_progress BOOLEAN, 
        started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
        finished_at TIMESTAMP WITHOUT TIME ZONE, 
        position VARCHAR NOT NULL, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        user_id INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(user_id) REFERENCES "user" (id)
)


CREATE TABLE project (
        id SERIAL NOT NULL, 
        title VARCHAR NOT NULL, 
        description VARCHAR, 
        price_from INTEGER NOT NULL, 
        price_to INTEGER NOT NULL, 
        expire_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
        finished_at TIMESTAMP WITHOUT TIME ZONE, 
        started_at TIMESTAMP WITHOUT TIME ZONE, 
        deadline_at TIMESTAMP WITHOUT TIME ZONE, 
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        owner_id INTEGER NOT NULL, 
        doer_id INTEGER, 
        status_id INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(owner_id) REFERENCES "user" (id), 
        FOREIGN KEY(doer_id) REFERENCES "user" (id), 
        FOREIGN KEY(status_id) REFERENCES status (id)
)


CREATE TABLE userverificationcode (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        code VARCHAR NOT NULL, 
        user_id INTEGER NOT NULL, 
        expire_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
        PRIMARY KEY (code), 
        UNIQUE (user_id), 
        FOREIGN KEY(user_id) REFERENCES "user" (id)
)


CREATE TABLE resetpasswordtoken (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        token VARCHAR NOT NULL, 
        user_id INTEGER NOT NULL, 
        expire_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
        PRIMARY KEY (token), 
        UNIQUE (user_id), 
        FOREIGN KEY(user_id) REFERENCES "user" (id)
)


CREATE TABLE follower (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        follower_id INTEGER NOT NULL, 
        following_id INTEGER NOT NULL, 
        PRIMARY KEY (follower_id, following_id), 
        FOREIGN KEY(follower_id) REFERENCES "user" (id), 
        FOREIGN KEY(following_id) REFERENCES "user" (id)
)


CREATE TABLE message (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        id SERIAL NOT NULL, 
        from_user_id INTEGER NOT NULL, 
        to_user_id INTEGER NOT NULL, 
        text VARCHAR NOT NULL, 
        is_read BOOLEAN NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(from_user_id) REFERENCES "user" (id), 
        FOREIGN KEY(to_user_id) REFERENCES "user" (id)
)


CREATE TABLE request (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        id SERIAL NOT NULL, 
        user_id INTEGER NOT NULL, 
        request_type VARCHAR NOT NULL, 
        accepted BOOLEAN, 
        responded_at TIMESTAMP WITHOUT TIME ZONE, 
        PRIMARY KEY (id), 
        FOREIGN KEY(user_id) REFERENCES "user" (id)
)


CREATE TABLE comment (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        star INTEGER NOT NULL, 
        project_id INTEGER NOT NULL, 
        from_user_id INTEGER NOT NULL, 
        to_user_id INTEGER NOT NULL, 
        message VARCHAR NOT NULL, 
        PRIMARY KEY (project_id, from_user_id), 
        FOREIGN KEY(project_id) REFERENCES project (id), 
        FOREIGN KEY(from_user_id) REFERENCES "user" (id), 
        FOREIGN KEY(to_user_id) REFERENCES "user" (id)
)


CREATE TABLE projecttechnology (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        technology_id INTEGER NOT NULL, 
        project_id INTEGER NOT NULL, 
        PRIMARY KEY (technology_id, project_id), 
        FOREIGN KEY(technology_id) REFERENCES technology (id), 
        FOREIGN KEY(project_id) REFERENCES project (id)
)


CREATE TABLE offer (
        updated_at TIMESTAMP WITHOUT TIME ZONE, 
        created_at TIMESTAMP WITHOUT TIME ZONE, 
        offerer_id INTEGER NOT NULL, 
        project_id INTEGER NOT NULL, 
        offer_price INTEGER NOT NULL, 
        duration_day INTEGER NOT NULL, 
        PRIMARY KEY (offerer_id, project_id), 
        FOREIGN KEY(offerer_id) REFERENCES "user" (id), 
        FOREIGN KEY(project_id) REFERENCES project (id)
)